from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.economics import estimate_cultivation_economics, calculate_crop_economics


def main():
    out = estimate_cultivation_economics({'crop':'paddy','area_value':1,'area_unit':'acre'})
    assert out['status'] == 'illustrative_planning_estimate'
    base = next(x for x in out['scenarios'] if x['name'] == 'Planning base')
    assert base['roi_pct'] is not None
    assert base['profit_margin_pct'] is not None
    assert base['cost_per_kg_lkr'] is not None
    exact = calculate_crop_economics(cost_lkr=100000, expected_yield_kg=1000, selling_price_lkr_per_kg=150)
    assert exact['revenue_lkr'] == 150000
    assert exact['profit_lkr'] == 50000
    assert exact['break_even_price_lkr_per_kg'] == 100
    print('MihiMura Phase 3 economics test: PASS')


if __name__ == '__main__':
    main()
