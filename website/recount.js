/* AgentMeasure browser-local recount.
 *
 * The same Tier 1 recount the Python CLI runs, in the browser, with no network
 * request after the page loads. Drop a counts-only export, get the statement.
 * Nothing is uploaded and no message text is read.
 *
 * Usage
 *   browser:  var am = AgentMeasureRecount(window.AGENTMEASURE_VENDOR_RULES);
 *   node:     var am = require('./recount.js')(require('./vendor-rules.js'));
 *
 * The vendor rules come from website/vendor-rules.js, generated from
 * registry/vendor-rules.json. A parity test in CI checks that this
 * implementation and healthcheck/am_healthcheck/vendors.py agree on the same
 * fixture, so the two cannot drift.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory;
  } else {
    root.AgentMeasureRecount = factory;
  }
})(typeof self !== "undefined" ? self : this, function (RULES) {
  "use strict";

  var BILLED_BUT_NOT_BILLABLE = "billed_but_not_billable";
  var BILLABLE_BUT_NOT_BILLED = "billable_but_not_billed";
  var CANNOT_SETTLE = "cannot_settle";
  var AGREES = "agrees";

  var TRUE_VALUES = ["yes", "true", "1", "y", "t"];
  var FALSE_VALUES = ["no", "false", "0", "n", "f"];

  if (!RULES) throw new Error("AgentMeasureRecount requires the vendor rules document");

  function asBool(value) {
    if (value === null || value === undefined) return null;
    var text = String(value).trim().toLowerCase();
    if (TRUE_VALUES.indexOf(text) !== -1) return true;
    if (FALSE_VALUES.indexOf(text) !== -1) return false;
    return null;
  }

  /* Minimal CSV parser: quoted fields, embedded commas and quotes. No
   * dependency, so the page stays a single offline artifact. */
  function parseCsv(text) {
    var rows = [], row = [], field = "", inQuotes = false;
    for (var i = 0; i < text.length; i++) {
      var c = text[i];
      if (inQuotes) {
        if (c === '"') {
          if (text[i + 1] === '"') { field += '"'; i++; }
          else { inQuotes = false; }
        } else { field += c; }
      } else if (c === '"') {
        inQuotes = true;
      } else if (c === ",") {
        row.push(field); field = "";
      } else if (c === "\n" || c === "\r") {
        if (c === "\r" && text[i + 1] === "\n") i++;
        row.push(field); field = "";
        if (row.length > 1 || row[0] !== "") rows.push(row);
        row = [];
      } else { field += c; }
    }
    if (field !== "" || row.length) {
      row.push(field);
      if (row.length > 1 || row[0] !== "") rows.push(row);
    }
    return rows;
  }

  function mapColumns(fieldnames) {
    var lowered = {};
    fieldnames.forEach(function (f) { lowered[String(f).trim().toLowerCase()] = f; });
    var mapping = {};
    Object.keys(RULES.column_aliases).forEach(function (canonical) {
      var list = RULES.column_aliases[canonical];
      for (var i = 0; i < list.length; i++) {
        if (Object.prototype.hasOwnProperty.call(lowered, list[i])) {
          mapping[canonical] = lowered[list[i]];
          break;
        }
      }
    });
    return mapping;
  }

  function loadExport(text) {
    var rows = parseCsv(text);
    if (!rows.length) {
      return { records: [], columns_found: [],
               columns_missing: RULES.required_columns.slice(), export_columns: [] };
    }
    var fieldnames = rows[0];
    var mapping = mapColumns(fieldnames);
    var missing = RULES.required_columns.filter(function (c) { return !mapping[c]; });
    var records = [];
    for (var i = 1; i < rows.length; i++) {
      var rec = {};
      Object.keys(mapping).forEach(function (canonical) {
        var idx = fieldnames.indexOf(mapping[canonical]);
        rec[canonical] = idx >= 0 ? rows[i][idx] : null;
      });
      RULES.required_columns.forEach(function (c) {
        if (!(c in rec)) rec[c] = null;
      });
      records.push(rec);
    }
    return {
      records: records,
      columns_found: Object.keys(mapping).sort(),
      columns_missing: missing,
      export_columns: fieldnames
    };
  }

  function judgeOne(rec, vendor) {
    var billed = asBool(rec.vendor_billed);
    var human = asBool(rec.human_agent_participated);
    var addressed = asBool(rec.issue_addressed);
    var recontacted = asBool(rec.customer_recontacted_within_window);

    /* Absent evidence cannot be decided: it lowers the verdict, never fills it. */
    if (billed === null || human === null || addressed === null || recontacted === null) {
      return CANNOT_SETTLE;
    }
    var shouldBill;
    if (human) {
      shouldBill = false;
    } else if (!addressed) {
      shouldBill = false;
    } else if (recontacted) {
      if (String(vendor.reopen_deduction).indexOf("documented") === 0) {
        shouldBill = false;
      } else {
        return CANNOT_SETTLE;   /* undocumented: we do not invent a rule */
      }
    } else {
      var trigger = vendor.billing_trigger;
      if (trigger === "confirmed_or_assumed" || trigger === "assumed_with_lock"
          || trigger === "algorithmic_classification") {
        shouldBill = true;
      } else if (trigger === "llm_verified_only") {
        /* The adjudication is the vendor's own model output; a counts-only
         * export does not carry it, so we do not invent it either way. */
        return CANNOT_SETTLE;
      } else {
        return CANNOT_SETTLE;
      }
    }
    if (billed && !shouldBill) return BILLED_BUT_NOT_BILLABLE;
    if (shouldBill && !billed) return BILLABLE_BUT_NOT_BILLED;
    return AGREES;
  }

  function round2(x) { return Math.round(x * 100) / 100; }
  function round4(x) { return Math.round(x * 10000) / 10000; }

  function recount(exportData, vendorId) {
    var vendor = RULES.vendors[vendorId];
    if (!vendor) throw new Error("unknown vendor: " + vendorId);
    var price = vendor.unit_price;

    var counts = {};
    counts[BILLED_BUT_NOT_BILLABLE] = 0;
    counts[BILLABLE_BUT_NOT_BILLED] = 0;
    counts[CANNOT_SETTLE] = 0;
    counts[AGREES] = 0;
    var billedCount = 0;
    var verdicts = [];
    exportData.records.forEach(function (rec, i) {
      var verdict = judgeOne(rec, vendor);
      counts[verdict]++;
      if (asBool(rec.vendor_billed)) billedCount++;
      verdicts.push({ line: i + 2, conversation_id: rec.conversation_id, verdict: verdict });
    });

    var over = counts[BILLED_BUT_NOT_BILLABLE];
    var under = counts[BILLABLE_BUT_NOT_BILLED];
    var cannot = counts[CANNOT_SETTLE];
    var total = exportData.records.length;

    var result = {
      vendor_id: vendorId,
      vendor_name: vendor.name,
      vendor_rule_confidence: vendor.confidence,
      vendor_rule_source: vendor.source,
      unit_price: price,
      currency: vendor.currency,
      total_conversations: total,
      billed_by_vendor: billedCount,
      counts: counts,
      net_findings: over - under,
      cannot_settle_share: total ? round4(cannot / total) : 0,
      columns_missing: exportData.columns_missing,
      verdicts: verdicts
    };
    if (price) {
      result.variance = round2((over - under) * price);
      result.overcharge_amount = round2(over * price);
      result.undercharge_amount = round2(under * price);
      result.cannot_settle_amount = round2(cannot * price);
    }
    return result;
  }

  return {
    BILLED_BUT_NOT_BILLABLE: BILLED_BUT_NOT_BILLABLE,
    BILLABLE_BUT_NOT_BILLED: BILLABLE_BUT_NOT_BILLED,
    CANNOT_SETTLE: CANNOT_SETTLE,
    AGREES: AGREES,
    parseCsv: parseCsv,
    loadExport: loadExport,
    recount: recount
  };
});
