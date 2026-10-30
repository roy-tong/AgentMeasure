"""SQLite 账本存储：幂等、修订链、冲销与有效行汇总（INV-1 / INV-2）。"""

import calendar
import datetime
import json
import sqlite3
from decimal import Decimal
from typing import List

from .model import (
    ChargeLine,
    EvidenceRef,
    LedgerError,
    PricingPolicy,
    ProviderAccount,
    SourceDocument,
    UsageEvent,
    sha,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS source_document (
  id TEXT PRIMARY KEY,
  content_hash TEXT NOT NULL,
  provider TEXT NOT NULL,
  tier TEXT NOT NULL,
  account_ref TEXT DEFAULT '',
  doc_type TEXT DEFAULT 'bill',
  period TEXT DEFAULT '',
  file_path TEXT DEFAULT '',
  file_name TEXT DEFAULT '',
  fetched_via TEXT DEFAULT 'manual_import',
  fetched_at TEXT DEFAULT '',
  extra_json TEXT DEFAULT '{}',
  UNIQUE(content_hash, provider, tier, account_ref, doc_type, period)
);
CREATE TABLE IF NOT EXISTS provider_account (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  account_ref TEXT NOT NULL,
  currency TEXT DEFAULT '',
  UNIQUE(provider, account_ref)
);
CREATE TABLE IF NOT EXISTS charge_line (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  currency TEXT NOT NULL,
  amount TEXT NOT NULL,
  description TEXT DEFAULT '',
  period TEXT DEFAULT '',
  line_no INTEGER,
  quantity TEXT DEFAULT '',
  unit TEXT DEFAULT '',
  unit_price TEXT DEFAULT '',
  tax TEXT DEFAULT '',
  charged_at TEXT DEFAULT '',
  tool TEXT DEFAULT '',
  review_status TEXT DEFAULT 'pending',
  evidence_json TEXT DEFAULT '[]',
  revision INTEGER DEFAULT 1,
  supersedes TEXT DEFAULT '',
  reversal_of TEXT DEFAULT '',
  note TEXT DEFAULT '',
  fingerprint TEXT NOT NULL,
  created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS usage_event (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  billable_unit TEXT NOT NULL,
  quantity TEXT NOT NULL,
  occurred_at TEXT DEFAULT '',
  period TEXT DEFAULT '',
  account_ref TEXT DEFAULT '',
  tool TEXT DEFAULT '',
  capability TEXT DEFAULT '',
  agent TEXT DEFAULT '',
  project TEXT DEFAULT '',
  currency TEXT DEFAULT '',
  unit_price_applied TEXT DEFAULT '',
  computed_charge TEXT,
  pricing_policy_id TEXT DEFAULT '',
  review_status TEXT DEFAULT 'pending',
  evidence_json TEXT DEFAULT '[]',
  revision INTEGER DEFAULT 1,
  supersedes TEXT DEFAULT '',
  reversal_of TEXT DEFAULT '',
  note TEXT DEFAULT '',
  fingerprint TEXT NOT NULL,
  created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS pricing_policy (
  id TEXT PRIMARY KEY,
  policy_id TEXT NOT NULL,
  version TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  currency TEXT DEFAULT 'USD',
  capability TEXT DEFAULT '',
  unit_price TEXT DEFAULT '',
  tiers_json TEXT DEFAULT '[]',
  free_quota TEXT DEFAULT '',
  valid_from TEXT DEFAULT '',
  valid_until TEXT DEFAULT '',
  source_document_id TEXT DEFAULT '',
  note TEXT DEFAULT '',
  UNIQUE(provider, policy_id, version, capability)
);
CREATE TABLE IF NOT EXISTS reconciliation (
  id TEXT PRIMARY KEY,
  period TEXT NOT NULL,
  provider TEXT NOT NULL,
  account_ref TEXT DEFAULT '',
  bill_total TEXT,
  recount_total TEXT,
  variance TEXT,
  variance_class TEXT NOT NULL,
  currency TEXT DEFAULT '',
  detail_json TEXT DEFAULT '{}',
  created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS parse_rule (
  fingerprint TEXT PRIMARY KEY,
  provider TEXT DEFAULT '',
  doc_type TEXT DEFAULT '',
  tier TEXT DEFAULT '',
  spec_json TEXT NOT NULL,
  created_via TEXT DEFAULT 'agent',
  golden_json TEXT DEFAULT '[]',
  version INTEGER DEFAULT 1,
  created_at TEXT DEFAULT '',
  approved INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_charge_period ON charge_line(period, provider);
CREATE INDEX IF NOT EXISTS idx_usage_period ON usage_event(period, provider);
CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_reversal_target
  ON usage_event(reversal_of) WHERE reversal_of <> '';
"""


def _evidence_to_json(evidence):
    return json.dumps([e.as_dict() for e in (evidence or [])], ensure_ascii=False)


def _evidence_from_json(text):
    return [EvidenceRef(**d) for d in json.loads(text or "[]")]


def _policy_date(value, month_end=False):
    if not value:
        return None
    raw = str(value)[:10]
    if len(raw) == 7:
        year, month = (int(p) for p in raw.split("-"))
        day = calendar.monthrange(year, month)[1] if month_end else 1
        return datetime.date(year, month, day)
    return datetime.date.fromisoformat(raw)


def _policy_active(row, at):
    """价格必须覆盖事件日；只有账期时，必须覆盖整个账期，避免月中串价。"""
    if not at:
        return True
    if len(str(at)) == 7:
        start = _policy_date(at)
        end = _policy_date(at, month_end=True)
    else:
        start = end = _policy_date(at)
    valid_from = _policy_date(row["valid_from"])
    valid_until = _policy_date(row["valid_until"], month_end=True)
    return ((valid_from is None or valid_from <= start) and
            (valid_until is None or valid_until >= end))


class LedgerStore:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        legacy_document = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='source_document'"
        ).fetchone()
        legacy_document = bool(
            legacy_document and "content_hash TEXT UNIQUE NOT NULL" in legacy_document["sql"])
        if legacy_document:
            self.conn.execute("ALTER TABLE source_document RENAME TO source_document_legacy")
        legacy_policy = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='pricing_policy'"
        ).fetchone()
        if legacy_policy and "UNIQUE(policy_id, version, capability)" in legacy_policy["sql"]:
            self.conn.execute("ALTER TABLE pricing_policy RENAME TO pricing_policy_legacy")
        self.conn.executescript(SCHEMA)
        document_id_map = self._copy_legacy_documents() if legacy_document else {}
        if legacy_policy and "UNIQUE(policy_id, version, capability)" in legacy_policy["sql"]:
            for row in self.conn.execute("SELECT * FROM pricing_policy_legacy"):
                values = dict(row)
                values["id"] = self._policy_row_id(
                    values["provider"], values["policy_id"], values["version"],
                    values["capability"])
                self.conn.execute(
                    "INSERT INTO pricing_policy VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tuple(values[k] for k in (
                        "id", "policy_id", "version", "provider", "model", "currency",
                        "capability", "unit_price", "tiers_json", "free_quota",
                        "valid_from", "valid_until", "source_document_id", "note")))
            self.conn.execute("DROP TABLE pricing_policy_legacy")
        if document_id_map:
            self._remap_document_references(document_id_map)
        # 小步前向迁移：M1 已创建的本地库无需删除重建。
        self._ensure_column("reconciliation", "currency", "TEXT DEFAULT ''")
        self._ensure_column("parse_rule", "approved", "INTEGER DEFAULT 0")
        self.conn.execute("UPDATE parse_rule SET approved=1 WHERE created_via='manual'")
        self.conn.commit()

    def _ensure_column(self, table, column, declaration):
        columns = {r["name"] for r in self.conn.execute("PRAGMA table_info(%s)" % table)}
        if column not in columns:
            self.conn.execute("ALTER TABLE %s ADD COLUMN %s %s" %
                              (table, column, declaration))

    def _copy_legacy_documents(self):
        mapping = {}
        for old in self.conn.execute("SELECT * FROM source_document_legacy").fetchall():
            doc = SourceDocument(
                content_hash=old["content_hash"], provider=old["provider"], tier=old["tier"],
                account_ref=old["account_ref"], doc_type=old["doc_type"],
                period=old["period"], file_path=old["file_path"],
                file_name=old["file_name"], fetched_via=old["fetched_via"],
                fetched_at=old["fetched_at"], extra=json.loads(old["extra_json"] or "{}"))
            mapping[old["id"]] = doc.id
            self.conn.execute(
                "INSERT INTO source_document VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (doc.id, doc.content_hash, doc.provider, doc.tier, doc.account_ref,
                 doc.doc_type, doc.period, doc.file_path, doc.file_name,
                 doc.fetched_via, doc.fetched_at, json.dumps(doc.extra, ensure_ascii=False)))
        return mapping

    def _remap_document_references(self, document_map):
        charge_id_map, usage_id_map = {}, {}
        for row in self.conn.execute("SELECT * FROM charge_line").fetchall():
            new_doc = document_map.get(row["document_id"], row["document_id"])
            evidence = json.loads(row["evidence_json"] or "[]")
            for ref in evidence:
                ref["document_id"] = document_map.get(ref.get("document_id"),
                                                      ref.get("document_id"))
            fingerprint = sha(row["provider"], new_doc, row["period"], row["line_no"],
                              row["description"], row["amount"], row["currency"],
                              row["revision"])
            new_id = "cl-" + fingerprint[:16]
            charge_id_map[row["id"]] = new_id
            self.conn.execute(
                "UPDATE charge_line SET id=?,document_id=?,fingerprint=?,evidence_json=? "
                "WHERE id=?", (new_id, new_doc, fingerprint,
                                json.dumps(evidence, ensure_ascii=False), row["id"]))
        for row in self.conn.execute("SELECT * FROM usage_event").fetchall():
            new_doc = document_map.get(row["document_id"], row["document_id"])
            evidence = json.loads(row["evidence_json"] or "[]")
            for ref in evidence:
                ref["document_id"] = document_map.get(ref.get("document_id"),
                                                      ref.get("document_id"))
            locator = evidence[0].get("locator", "") if evidence else ""
            fingerprint = sha(row["provider"], new_doc, row["occurred_at"], row["tool"],
                              row["capability"], row["billable_unit"], row["quantity"],
                              row["period"], row["account_ref"], row["agent"],
                              row["project"], locator, row["revision"])
            new_id = "ue-" + fingerprint[:16]
            usage_id_map[row["id"]] = new_id
            self.conn.execute(
                "UPDATE usage_event SET id=?,document_id=?,fingerprint=?,evidence_json=? "
                "WHERE id=?", (new_id, new_doc, fingerprint,
                                json.dumps(evidence, ensure_ascii=False), row["id"]))
        for table, mapping in (("charge_line", charge_id_map),
                               ("usage_event", usage_id_map)):
            for old_id, new_id in mapping.items():
                self.conn.execute(
                    "UPDATE %s SET supersedes=?,reversal_of=? WHERE id=?" % table,
                    (mapping.get(self.conn.execute(
                        "SELECT supersedes FROM %s WHERE id=?" % table,
                        (new_id,)).fetchone()[0], ""),
                     mapping.get(self.conn.execute(
                         "SELECT reversal_of FROM %s WHERE id=?" % table,
                         (new_id,)).fetchone()[0], ""), new_id))
        for old_id, new_id in document_map.items():
            self.conn.execute("UPDATE pricing_policy SET source_document_id=? "
                              "WHERE source_document_id=?", (new_id, old_id))
        # 快照包含旧行 ID；清除后由用户重跑，原始行与证据已完整迁移。
        self.conn.execute("DELETE FROM reconciliation")
        self.conn.execute("DROP TABLE source_document_legacy")

    def close(self):
        self.conn.close()

    # ── documents ──────────────────────────────────────────────────────

    def put_document(self, doc: SourceDocument) -> str:
        """同哈希同语义入档幂等；同哈希换平台/账户/账期必须显式报错。"""
        existing = self.get_document(doc.id)
        if existing:
            expected = (doc.provider, doc.tier, doc.account_ref, doc.doc_type, doc.period)
            actual = tuple(existing[k] for k in
                           ("provider", "tier", "account_ref", "doc_type", "period"))
            if actual != expected:
                raise LedgerError(
                    "content hash already registered with different provider/tier/"
                    "account/doc_type/period; refusing to relabel evidence")
            return doc.id, False
        try:
            self.conn.execute(
                "INSERT INTO source_document VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (doc.id, doc.content_hash, doc.provider, doc.tier, doc.account_ref,
                 doc.doc_type, doc.period, doc.file_path, doc.file_name,
                 doc.fetched_via, doc.fetched_at,
                 json.dumps(doc.extra, ensure_ascii=False)),
            )
            self.conn.commit()
            return doc.id, True
        except sqlite3.IntegrityError as exc:
            raise LedgerError("document identity conflict: %s" % exc)

    def get_document(self, doc_id):
        row = self.conn.execute(
            "SELECT * FROM source_document WHERE id=?", (doc_id,)).fetchone()
        return dict(row) if row else None

    def list_documents(self, provider=None, tier=None, period=None):
        sql, args = "SELECT * FROM source_document WHERE 1=1", []
        if provider:
            sql += " AND provider=?"
            args.append(provider)
        if tier:
            sql += " AND tier=?"
            args.append(tier)
        if period:
            sql += " AND period=?"
            args.append(period)
        return [dict(r) for r in self.conn.execute(sql + " ORDER BY id", args)]

    # ── accounts / policies ───────────────────────────────────────────

    def put_account(self, acct: ProviderAccount):
        self.conn.execute(
            "INSERT OR IGNORE INTO provider_account VALUES (?,?,?,?)",
            (acct.id, acct.provider, acct.account_ref, acct.currency))
        self.conn.commit()

    @staticmethod
    def _policy_row_id(provider, policy_id, version, capability):
        return "%s:%s@%s/%s" % (provider, policy_id, version,
                                capability or "default")

    def put_policy(self, p: PricingPolicy):
        """政策身份含 provider；同版本不可变，改价必须发布新版本。"""
        row_id = self._policy_row_id(p.provider, p.policy_id, p.version, p.capability)
        values = (row_id, p.policy_id, p.version, p.provider,
                  p.model, p.currency, p.capability, p.unit_price,
                  json.dumps(p.tiers, ensure_ascii=False), p.free_quota,
                  p.valid_from, p.valid_until, p.source_document_id, p.note)
        existing = self.conn.execute(
            "SELECT * FROM pricing_policy WHERE id=?", (row_id,)).fetchone()
        if existing:
            old = tuple(existing[k] for k in (
                "id", "policy_id", "version", "provider", "model", "currency",
                "capability", "unit_price", "tiers_json", "free_quota",
                "valid_from", "valid_until", "source_document_id", "note"))
            if old != values:
                raise LedgerError(
                    "pricing policy version is immutable; publish a new version")
            return row_id, False
        self.conn.execute(
            "INSERT INTO pricing_policy VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
        self.conn.commit()
        return row_id, True

    def find_policy(self, provider, capability="", at=""):
        """匹配 provider+capability → provider 默认；同一级有歧义则放弃计价。"""
        for cap in ([capability] if capability else []) + [""]:
            rows = self.conn.execute(
                "SELECT * FROM pricing_policy WHERE provider=? AND capability=? "
                "ORDER BY valid_from DESC, rowid DESC", (provider, cap)).fetchall()
            active = [r for r in rows if _policy_active(r, at)]
            if not active:
                continue
            if len(active) != 1:
                return None
            r = dict(active[0])
            return PricingPolicy(
                policy_id=r["policy_id"], version=r["version"], provider=r["provider"],
                model=r["model"], currency=r["currency"], capability=r["capability"],
                unit_price=r["unit_price"], tiers=json.loads(r["tiers_json"] or "[]"),
                free_quota=r["free_quota"], valid_from=r["valid_from"],
                valid_until=r["valid_until"], source_document_id=r["source_document_id"],
                note=r["note"])
        return None

    # ── charge lines / usage events ───────────────────────────────────

    def _validate_document_scope(self, document_id, provider, expected_tier):
        doc = self.get_document(document_id)
        if not doc:
            raise LedgerError("source document not found: %s" % document_id)
        if doc["provider"] != provider or doc["tier"] != expected_tier:
            raise LedgerError("row provider/tier does not match its source document")
        return doc

    @staticmethod
    def _row_account(row, documents):
        return row.get("account_ref") or documents[row["document_id"]]["account_ref"]

    def _validate_supersedes(self, table, row_id, provider, revision, supersedes,
                             currency=None, account=None):
        if not supersedes:
            return
        target = self.conn.execute(
            "SELECT * FROM %s WHERE id=?" % table, (supersedes,)).fetchone()
        if not target:
            raise LedgerError("supersedes target not found: %s" % supersedes)
        if target["provider"] != provider:
            raise LedgerError("cannot supersede a row from another provider")
        if target["reversal_of"]:
            raise LedgerError("cannot supersede a reversal row")
        if self.conn.execute("SELECT 1 FROM %s WHERE reversal_of=?" % table,
                             (supersedes,)).fetchone():
            raise LedgerError("cannot supersede an already reversed row")
        if revision <= target["revision"]:
            raise LedgerError("revision must increase along supersedes chain")
        if currency is not None and target["currency"] != currency:
            raise LedgerError("cannot supersede across currencies")
        successor = self.conn.execute(
            "SELECT id FROM %s WHERE supersedes=? AND id<>?" % table,
            (supersedes, row_id)).fetchone()
        if successor:
            raise LedgerError("supersedes branch refused: target already has a successor")
        if account is not None:
            documents = {d["id"]: d for d in self.list_documents()}
            old_account = target["account_ref"] if table == "usage_event" else ""
            old_account = old_account or documents[target["document_id"]]["account_ref"]
            if old_account != account:
                raise LedgerError("cannot supersede across accounts")

    def put_charge_line(self, cl: ChargeLine, commit=True):
        """指纹幂等；文档作用域、唯一修订链和有界冲销在入库时强制。"""
        doc = self._validate_document_scope(cl.document_id, cl.provider, "bill_fact")
        self._validate_supersedes(
            "charge_line", cl.id, cl.provider, cl.revision, cl.supersedes,
            currency=cl.currency, account=doc["account_ref"])
        if cl.reversal_of:
            target = self.conn.execute(
                "SELECT * FROM charge_line WHERE id=?", (cl.reversal_of,)).fetchone()
            if not target or target["provider"] != cl.provider:
                raise LedgerError("reversal target not found in provider scope")
            if target["currency"] != cl.currency or target["reversal_of"]:
                raise LedgerError("reversal must target an original row in the same currency")
            if self.conn.execute("SELECT 1 FROM charge_line WHERE supersedes=?",
                                 (cl.reversal_of,)).fetchone():
                raise LedgerError("cannot reverse a superseded row; reverse the current head")
            target_doc = self.get_document(target["document_id"])
            if target_doc["account_ref"] != doc["account_ref"]:
                raise LedgerError("cannot reverse across accounts")
            if Decimal(target["amount"]) <= 0:
                raise LedgerError("reversal target must have a positive amount")
            previous = self.conn.execute(
                "SELECT amount FROM charge_line WHERE reversal_of=? AND id<>?",
                (cl.reversal_of, cl.id)).fetchall()
            reversed_amount = sum((Decimal(r["amount"]) for r in previous), Decimal("0"))
            if reversed_amount + Decimal(cl.amount) < -Decimal(target["amount"]):
                raise LedgerError("reversals exceed original amount")
        try:
            self.conn.execute(
                "INSERT INTO charge_line VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cl.id, cl.document_id, cl.provider, cl.currency, cl.amount,
                 cl.description, cl.period, cl.line_no, cl.quantity, cl.unit,
                 cl.unit_price, cl.tax, cl.charged_at, cl.tool, cl.review_status,
                 _evidence_to_json(cl.evidence), cl.revision, cl.supersedes,
                 cl.reversal_of, cl.note, cl.fingerprint,
                 datetime.datetime.utcnow().isoformat() + "Z"))
            if commit:
                self.conn.commit()
            return cl.id, True
        except sqlite3.IntegrityError as exc:
            if self.conn.execute("SELECT 1 FROM charge_line WHERE id=?", (cl.id,)).fetchone():
                return cl.id, False
            raise LedgerError("charge line integrity failure: %s" % exc)

    def put_usage_event(self, ue: UsageEvent, commit=True):
        doc = self._validate_document_scope(ue.document_id, ue.provider, "platform_usage")
        if ue.computed_charge is not None and not ue.reversal_of:
            raise LedgerError(
                "computed_charge can only be written by apply_pricing; import unpriced usage")
        if ue.account_ref and doc["account_ref"] and ue.account_ref != doc["account_ref"]:
            raise LedgerError("usage account does not match source document account")
        account = ue.account_ref or doc["account_ref"]
        self._validate_supersedes(
            "usage_event", ue.id, ue.provider, ue.revision, ue.supersedes, account=account)
        if ue.reversal_of:
            target = self.conn.execute(
                "SELECT * FROM usage_event WHERE id=?", (ue.reversal_of,)).fetchone()
            if not target or target["provider"] != ue.provider:
                raise LedgerError("usage reversal target not found in provider scope")
            if target["reversal_of"] or self.conn.execute(
                    "SELECT 1 FROM usage_event WHERE supersedes=?",
                    (ue.reversal_of,)).fetchone():
                raise LedgerError("usage reversal target must be a current original event")
            if self.conn.execute(
                    "SELECT 1 FROM usage_event WHERE reversal_of=? AND id<>?",
                    (ue.reversal_of, ue.id)).fetchone():
                raise LedgerError("usage target already has a full reversal")
            target_doc = self.get_document(target["document_id"])
            target_account = target["account_ref"] or target_doc["account_ref"]
            if target_account != account:
                raise LedgerError("cannot reverse usage across accounts")
            if target["billable_unit"] != ue.billable_unit:
                raise LedgerError("cannot reverse usage across billable units")
            if Decimal(ue.quantity) >= 0 or Decimal(target["quantity"]) <= 0:
                raise LedgerError("usage reversal must be negative and target positive usage")
            if Decimal(ue.quantity) + Decimal(target["quantity"]) != 0:
                raise LedgerError("usage reversal must exactly offset target quantity")
            if (ue.computed_charge is None) != (target["computed_charge"] is None):
                raise LedgerError("usage reversal pricing state must match target")
            if ue.computed_charge is not None and (
                    ue.currency != target["currency"] or
                    ue.pricing_policy_id != target["pricing_policy_id"] or
                    Decimal(ue.computed_charge) + Decimal(target["computed_charge"]) != 0):
                raise LedgerError("usage reversal must exactly offset target charge and policy")
        try:
            self.conn.execute(
                "INSERT INTO usage_event VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ue.id, ue.document_id, ue.provider, ue.billable_unit, ue.quantity,
                 ue.occurred_at, ue.period, ue.account_ref, ue.tool, ue.capability,
                 ue.agent, ue.project, ue.currency, ue.unit_price_applied,
                 ue.computed_charge, ue.pricing_policy_id, ue.review_status,
                 _evidence_to_json(ue.evidence), ue.revision, ue.supersedes,
                 ue.reversal_of, ue.note, ue.fingerprint,
                 datetime.datetime.utcnow().isoformat() + "Z"))
            if commit:
                self.conn.commit()
            return ue.id, True
        except sqlite3.IntegrityError as exc:
            if self.conn.execute("SELECT 1 FROM usage_event WHERE id=?", (ue.id,)).fetchone():
                return ue.id, False
            raise LedgerError("usage event integrity failure: %s" % exc)

    def _superseded_ids(self, table):
        rows = self.conn.execute(
            "SELECT supersedes FROM %s WHERE supersedes != ''" % table).fetchall()
        return {r["supersedes"] for r in rows}

    def effective_charge_lines(self, period=None, provider=None) -> List[dict]:
        """有效行 = 未被任何修订取代的行（INV-2）。冲销行本身是事实，保留负额。"""
        superseded = self._superseded_ids("charge_line")
        sql, args = "SELECT * FROM charge_line WHERE 1=1", []
        if period:
            sql += " AND period=?"
            args.append(period)
        if provider:
            sql += " AND provider=?"
            args.append(provider)
        out = []
        for r in self.conn.execute(sql + " ORDER BY provider, period, line_no", args):
            d = dict(r)
            if d["id"] in superseded:
                continue
            d["evidence"] = _evidence_from_json(d.pop("evidence_json"))
            out.append(d)
        return out

    def effective_usage_events(self, period=None, provider=None) -> List[dict]:
        superseded = self._superseded_ids("usage_event")
        sql, args = "SELECT * FROM usage_event WHERE 1=1", []
        if period:
            sql += " AND period=?"
            args.append(period)
        if provider:
            sql += " AND provider=?"
            args.append(provider)
        out = []
        for r in self.conn.execute(sql + " ORDER BY provider, occurred_at", args):
            d = dict(r)
            if d["id"] in superseded:
                continue
            d["evidence"] = _evidence_from_json(d.pop("evidence_json"))
            out.append(d)
        return out

    def count_rows_for_document(self, doc_id):
        n1 = self.conn.execute(
            "SELECT COUNT(*) c FROM charge_line WHERE document_id=?",
            (doc_id,)).fetchone()["c"]
        n2 = self.conn.execute(
            "SELECT COUNT(*) c FROM usage_event WHERE document_id=?",
            (doc_id,)).fetchone()["c"]
        return n1 + n2

    # ── parse rules ────────────────────────────────────────────────────

    @staticmethod
    def _parse_rule_key(fingerprint, provider="", doc_type="", tier=""):
        if not (provider or doc_type or tier):
            return fingerprint
        return sha(fingerprint, provider, doc_type, tier)

    def put_parse_rule(self, fingerprint, spec, provider="", doc_type="",
                       tier="", created_via="agent", golden=None, approved=None):
        if approved is None:
            approved = created_via != "agent"
        key = self._parse_rule_key(fingerprint, provider, doc_type, tier)
        self.conn.execute(
            "INSERT OR REPLACE INTO parse_rule "
            "(fingerprint,provider,doc_type,tier,spec_json,created_via,golden_json,"
            "version,created_at,approved) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (key, provider, doc_type, tier,
             json.dumps(spec, ensure_ascii=False), created_via,
             json.dumps(golden or [], ensure_ascii=False), 1,
             datetime.datetime.utcnow().isoformat() + "Z", 1 if approved else 0))
        self.conn.commit()
        return key

    def get_parse_rule(self, fingerprint, provider="", doc_type="", tier=""):
        key = self._parse_rule_key(fingerprint, provider, doc_type, tier)
        row = self.conn.execute(
            "SELECT * FROM parse_rule WHERE fingerprint=?", (key,)).fetchone()
        if not row and key != fingerprint:
            # 兼容早期未加作用域的库，但元数据必须完全一致，不能跨平台重放。
            row = self.conn.execute(
                "SELECT * FROM parse_rule WHERE fingerprint=? AND provider=? "
                "AND doc_type=? AND tier=?",
                (fingerprint, provider, doc_type, tier)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["approved"] = bool(d["approved"])
        d["spec"] = json.loads(d.pop("spec_json"))
        d["golden"] = json.loads(d.pop("golden_json") or "[]")
        return d

    def approve_parse_rule(self, fingerprint, provider="", doc_type="", tier=""):
        rule = self.get_parse_rule(fingerprint, provider, doc_type, tier)
        if not rule:
            raise LedgerError("parse rule not found")
        self.conn.execute("UPDATE parse_rule SET approved=1 WHERE fingerprint=?",
                          (rule["fingerprint"],))
        self.conn.commit()
        rule["approved"] = True
        return rule

    def list_parse_rules(self):
        rows = []
        for row in self.conn.execute("SELECT * FROM parse_rule ORDER BY created_at"):
            d = dict(row)
            d["approved"] = bool(d["approved"])
            d["spec"] = json.loads(d.pop("spec_json"))
            d["golden"] = json.loads(d.pop("golden_json") or "[]")
            rows.append(d)
        return rows

    # ── reconciliation results ─────────────────────────────────────────

    def put_reconciliation(self, period, provider, account_ref, bill_total,
                           recount_total, variance, variance_class, detail,
                           currency="", commit=True):
        rid = "rc-" + sha(period, provider, account_ref, currency)[:24]
        self.conn.execute(
            "INSERT OR REPLACE INTO reconciliation "
            "(id,period,provider,account_ref,bill_total,recount_total,variance,"
            "variance_class,currency,detail_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (rid, period, provider, account_ref,
             None if bill_total is None else str(bill_total),
             None if recount_total is None else str(recount_total),
             None if variance is None else str(variance),
             variance_class, currency, json.dumps(detail, ensure_ascii=False),
             datetime.datetime.utcnow().isoformat() + "Z"))
        if commit:
            self.conn.commit()

    def list_reconciliations(self, period):
        rows = self.conn.execute(
            "SELECT * FROM reconciliation WHERE period=? ORDER BY provider", (period,))
        return [dict(r) for r in rows]
