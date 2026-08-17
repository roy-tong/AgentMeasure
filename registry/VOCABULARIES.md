# AgentMeasure — Vocabulary Registry（由 scripts/gen_vocab.py 生成，勿手改）

> 单一事实源：`registry/vocabularies.yaml`（vocab revision 0.4.3-2）。
> 消费者：`schemas/observation.schema.json`（生成）· `sdk/src/index.ts`（CI 校验）·
> `reference/collector/usage.py`（CI 校验）。

## usage_context — Usage Context（Core §7，数据环境语义）

```text
production · development · test · benchmark · evaluation · synthetic · ci · demo · unknown
```

## validity — Validity（Core §7，执行有效性）

```text
normal · duplicate · replay · health_check · load_test · suspected_invalid · unknown
```

## context_source — Context Source

```text
none · provider_configuration · collector_derived · runtime_propagated
```

## validity_source — Validity Source

```text
none · provider_configuration · collector_derived · runtime_propagated
```

## caller_type — Caller Type（TRUST §5）

```text
unknown · claimed_agent · correlated_agent · platform_attested
```

## caller_identity_strength — Caller Identity Strength（TRUST §5）

```text
unknown · declared · correlated · attested
```

## observer_side — Observer Side

```text
client · server · platform
```

## provenance — Provenance

```text
hook · otel · wrapper · platform
```

## observation_type — Observation Type（DATA §1）

```text
presentation · selection · attempt_started · attempt_completed · result_consumed · task_outcome
```

## choice_mode — Choice Mode（Core §6 三轴）

```text
exclusive · multi_select · parallel · sequential · ordered_fallback · router_preselected · unknown
```

## decision_authority — Decision Authority（Core §6 三轴）

```text
model · router · workflow · user · policy · platform · unknown
```

## selection_constraint — Selection Constraint（Core §6 三轴）

```text
autonomous · recommended · required · user_requested · fallback · forced · unknown
```
