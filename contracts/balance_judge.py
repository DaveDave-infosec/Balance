# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import json


BALANCE_PROMPT = """You are Balance, an impartial settlement judge. Your job is to decide how much
of a digital deliverable was actually fulfilled, as a single percentage from 0
to 100, judged strictly against the acceptance criteria that BOTH parties locked
in before any work or dispute.

LOCKED ACCEPTANCE CRITERIA (the neutral yardstick — neither party can change this):
{spec}

DELIVERER'S SUBMITTED STATEMENT (a claim, NOT fact):
{deliverer_statement}

DELIVERER'S EVIDENCE (content fetched live from the URLs they submitted):
{deliverer_evidence}

PAYER'S SUBMITTED STATEMENT (a claim, NOT fact):
{payer_statement}

PAYER'S EVIDENCE (content fetched live from the URLs they submitted):
{payer_evidence}

How to judge:
1. VERIFY, DON'T TRUST. Never take either party's written statement as fact.
   Judge only against what the fetched evidence actually shows. If a party
   claims something ("auth works", "the site is deployed") but the fetched
   content does not show it, the claim is unsupported.
2. BROKEN OR EMPTY IS A SIGNAL. If a resource is NOT_PROVIDED,
   FETCH_FAILED_OR_UNREACHABLE, EMPTY_RESOURCE, or clearly unrelated to the
   spec, that counts AGAINST any claim depending on it. A party pointing at a
   404 or an empty repo has not demonstrated that work.
3. INVESTIGATE DIVERGENCE. Where the two parties' evidence disagrees (e.g. they
   point at different repos, or one says deployed and the other shows a dead
   link), rely on what the fetched content actually contains. The divergence
   itself is informative.
4. SCORE EACH CRITERION, THEN AGGREGATE. Break the locked criteria into
   checkable items. For each, decide from the evidence whether it is fully met,
   partially met, or not met. Aggregate into one fulfillment_pct that fairly
   reflects how much of the whole deliverable is demonstrably done. Partial,
   good-faith work should land in the middle — not 0, not 100.
5. ONLY JUDGE WHAT IS CHECKABLE. If a criterion cannot be verified from
   web-fetchable evidence, say so in your reasoning and do not let it swing the
   score in either direction.

Respond ONLY as valid JSON, no markdown, no preamble:
{{
  "fulfillment_pct": 0-100,
  "confidence_level": "High" or "Moderate" or "Low" or "Contested",
  "deliverer_evidence_assessment": "1 sentence on what the deliverer's fetched resources actually showed",
  "payer_evidence_assessment": "1 sentence on what the payer's fetched resources actually showed",
  "divergence_note": "1 sentence on where the two bundles diverged and what you found when you looked",
  "reasoning_summary": "2-3 sentences explaining the fulfillment percentage, grounded in the fetched evidence, as a neutral arbiter would",
  "minority_note": "1-2 sentences giving the strongest good-faith case that the percentage should be materially higher or lower — the dissenting view, preserved"
}}"""


class BalanceJudge(gl.Contract):
    verdict_ids: DynArray[str]
    case_id: TreeMap[str, str]
    spec_used: TreeMap[str, str]
    fulfillment_pct: TreeMap[str, u64]
    confidence_level: TreeMap[str, str]
    deliverer_evidence_assessment: TreeMap[str, str]
    payer_evidence_assessment: TreeMap[str, str]
    divergence_note: TreeMap[str, str]
    reasoning_summary: TreeMap[str, str]
    minority_note: TreeMap[str, str]
    deliverer_primary_url: TreeMap[str, str]
    deliverer_secondary_url: TreeMap[str, str]
    deliverer_statement: TreeMap[str, str]
    payer_primary_url: TreeMap[str, str]
    payer_secondary_url: TreeMap[str, str]
    payer_statement: TreeMap[str, str]
    payer_address: TreeMap[str, str]
    deliverer_address: TreeMap[str, str]
    requested_at: TreeMap[str, str]
    verdict_counter: u64

    def __init__(self):
        self.verdict_counter = 0

    @gl.public.write
    def judge_fulfillment(
        self,
        case_id: str,
        locked_spec: str,
        deliverer_primary_url: str,
        deliverer_secondary_url: str,
        deliverer_statement: str,
        payer_primary_url: str,
        payer_secondary_url: str,
        payer_statement: str,
        payer_address: str,
        deliverer_address: str,
        requested_at: str,
    ) -> str:
        # Copy everything the non-det closures need into locals; `self` is NOT
        # accessible inside strict_eq / prompt_comparative blocks.
        spec_local = locked_spec
        del_primary = deliverer_primary_url
        del_secondary = deliverer_secondary_url
        del_statement = deliverer_statement
        pay_primary = payer_primary_url
        pay_secondary = payer_secondary_url
        pay_statement = payer_statement

        def _fetch_one(url: str) -> str:
            if not url or not url.strip():
                return "NOT_PROVIDED"
            try:
                content = gl.nondet.web.render(url, mode="text")
                if content is None:
                    return "FETCH_FAILED_OR_UNREACHABLE"
                text = str(content).strip()
                if text == "":
                    return "EMPTY_RESOURCE"
                return text[:4000]
            except Exception:
                return "FETCH_FAILED_OR_UNREACHABLE"

        def fetch_deliverer() -> str:
            out = {
                "primary_url": del_primary,
                "primary_content": _fetch_one(del_primary),
                "secondary_url": del_secondary,
                "secondary_content": _fetch_one(del_secondary),
            }
            return json.dumps(out, sort_keys=True)
        deliverer_evidence = gl.eq_principle.strict_eq(fetch_deliverer)

        def fetch_payer() -> str:
            out = {
                "primary_url": pay_primary,
                "primary_content": _fetch_one(pay_primary),
                "secondary_url": pay_secondary,
                "secondary_content": _fetch_one(pay_secondary),
            }
            return json.dumps(out, sort_keys=True)
        payer_evidence = gl.eq_principle.strict_eq(fetch_payer)

        del_evidence_local = deliverer_evidence
        pay_evidence_local = payer_evidence

        def judge_fn() -> str:
            prompt = BALANCE_PROMPT.format(
                spec=spec_local,
                deliverer_statement=del_statement,
                deliverer_evidence=del_evidence_local,
                payer_statement=pay_statement,
                payer_evidence=pay_evidence_local,
            )
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            if isinstance(result, str):
                parsed = json.loads(result)
            else:
                parsed = result
            return json.dumps(parsed, sort_keys=True)
        principle = (
            "The verdict must agree on fulfillment_pct within a tolerance of 10 "
            "points. It must agree on the coarse outcome band: not fulfilled "
            "(0-33), partially fulfilled (34-66), or substantially fulfilled "
            "(67-100). The reasoning must be grounded in the fetched evidence and "
            "the locked acceptance criteria, never in either party's self-description."
        )
        judgment_str = gl.eq_principle.prompt_comparative(judge_fn, principle)
        judgment = json.loads(judgment_str)

        pct_raw = judgment.get("fulfillment_pct", 0)
        try:
            pct_int = int(pct_raw)
        except (TypeError, ValueError):
            pct_int = 0
        if pct_int < 0:
            pct_int = 0
        if pct_int > 100:
            pct_int = 100

        verdict_id = "balance_" + str(self.verdict_counter)
        self.case_id[verdict_id] = case_id
        self.spec_used[verdict_id] = locked_spec
        self.fulfillment_pct[verdict_id] = u64(pct_int)
        self.confidence_level[verdict_id] = str(judgment.get("confidence_level", "Low"))
        self.deliverer_evidence_assessment[verdict_id] = str(judgment.get("deliverer_evidence_assessment", ""))
        self.payer_evidence_assessment[verdict_id] = str(judgment.get("payer_evidence_assessment", ""))
        self.divergence_note[verdict_id] = str(judgment.get("divergence_note", ""))
        self.reasoning_summary[verdict_id] = str(judgment.get("reasoning_summary", ""))
        self.minority_note[verdict_id] = str(judgment.get("minority_note", ""))
        self.deliverer_primary_url[verdict_id] = deliverer_primary_url
        self.deliverer_secondary_url[verdict_id] = deliverer_secondary_url
        self.deliverer_statement[verdict_id] = deliverer_statement
        self.payer_primary_url[verdict_id] = payer_primary_url
        self.payer_secondary_url[verdict_id] = payer_secondary_url
        self.payer_statement[verdict_id] = payer_statement
        self.payer_address[verdict_id] = payer_address.lower()
        self.deliverer_address[verdict_id] = deliverer_address.lower()
        self.requested_at[verdict_id] = requested_at
        self.verdict_ids.append(verdict_id)
        self.verdict_counter = self.verdict_counter + 1
        return verdict_id

    def _build_verdict(self, verdict_id: str) -> dict:
        return {
            "verdict_id": verdict_id,
            "case_id": self.case_id[verdict_id],
            "fulfillment_pct": self.fulfillment_pct[verdict_id],
            "confidence_level": self.confidence_level[verdict_id],
            "deliverer_evidence_assessment": self.deliverer_evidence_assessment[verdict_id],
            "payer_evidence_assessment": self.payer_evidence_assessment[verdict_id],
            "divergence_note": self.divergence_note[verdict_id],
            "reasoning_summary": self.reasoning_summary[verdict_id],
            "minority_note": self.minority_note[verdict_id],
            "spec_used": self.spec_used[verdict_id],
            "deliverer_primary_url": self.deliverer_primary_url[verdict_id],
            "deliverer_secondary_url": self.deliverer_secondary_url[verdict_id],
            "deliverer_statement": self.deliverer_statement[verdict_id],
            "payer_primary_url": self.payer_primary_url[verdict_id],
            "payer_secondary_url": self.payer_secondary_url[verdict_id],
            "payer_statement": self.payer_statement[verdict_id],
            "payer_address": self.payer_address[verdict_id],
            "deliverer_address": self.deliverer_address[verdict_id],
            "requested_at": self.requested_at[verdict_id],
        }

    @gl.public.view
    def get_verdict(self, verdict_id: str) -> dict:
        if verdict_id not in self.case_id:
            return {}
        return self._build_verdict(verdict_id)

    @gl.public.view
    def get_all_verdicts(self) -> list:
        out = []
        for i in range(len(self.verdict_ids) - 1, -1, -1):
            out.append(self._build_verdict(self.verdict_ids[i]))
        return out

    @gl.public.view
    def get_verdicts_by_case(self, case_id: str) -> list:
        out = []
        for i in range(len(self.verdict_ids) - 1, -1, -1):
            vid = self.verdict_ids[i]
            if self.case_id[vid] == case_id:
                out.append(self._build_verdict(vid))
        return out

    @gl.public.view
    def get_verdict_count(self) -> u64:
        return u64(len(self.verdict_ids))
