from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.evidence_validation import assess_evidence, validate_response_claims
from app.services.tool_planner import build_tool_plan


def main():
    plan = build_tool_plan('input_safety_decision','decision_support','Can I apply fertilizer tomorrow?',{'crop':'Paddy','location':'Galle'}).to_dict()
    evidence = assess_evidence(
        plan=plan,
        context={'crop':'Paddy','location':'Galle'},
        weather_decision={'decision_usable':True},
        knowledge={'retrieval':'hybrid_pgvector_fts','documents':[{'title':'Rice guide'}]},
        market={}, economics={}, water={},
        safety={'hazardous_or_rate_sensitive':False},
    )
    assert evidence['level'] in {'high','moderate'}
    result = validate_response_claims({'confidence':0.99,'agent_trace':[],'do_not_do':[]}, evidence, {'hazardous_or_rate_sensitive':False})
    assert result['confidence'] == evidence['score']
    assert result['model_confidence'] == 0.99

    weak = assess_evidence(
        plan=plan,
        context={'crop':'Paddy','location':'Galle'},
        weather_decision={'decision_usable':False},
        knowledge={'retrieval':'approved_source_registry_fallback','documents':[]},
        market={}, economics={}, water={},
        safety={'hazardous_or_rate_sensitive':True},
    )
    assert weak['level'] in {'low','insufficient'}
    assert weak['can_make_current_decision'] is False
    assert weak['can_make_rate_sensitive_recommendation'] is False
    print('MihiMura Phase 3 evidence/confidence test: PASS')


if __name__ == '__main__':
    main()
