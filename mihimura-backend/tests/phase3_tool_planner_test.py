from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.tool_planner import build_tool_plan


def main():
    p = build_tool_plan('weather_decision', 'decision_support', 'Should I apply fertilizer tomorrow if rain is expected?', {'crop':'Paddy','location':'Galle'})
    b = p.bool_map()
    assert b['weather'] is True
    assert b['agronomy'] is True
    assert b['safety'] is True
    assert b['market'] is False

    m = build_tool_plan('market_decision', 'decision_support', 'Where can I sell my paddy and what is the current market price?', {'crop':'Paddy'})
    mb = m.bool_map()
    assert mb['market'] is True
    assert mb['weather'] is False

    r = build_tool_plan('cultivation_report', 'full_report', 'Give me a full paddy cultivation report with equipment cost and profit', {'crop':'Paddy'})
    rb = r.bool_map()
    assert rb['economics'] and rb['resources'] and rb['market']
    print('MihiMura Phase 3 tool-planner test: PASS')


if __name__ == '__main__':
    main()
