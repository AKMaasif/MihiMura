from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.weather_decision import build_weather_decision_context


def main():
    weather = {
        'status':'success','live':True,'source':'Open-Meteo','retrieved_at':'now',
        'current':{'temperature_2m':30,'relative_humidity_2m':80,'precipitation':0,'wind_speed_10m':12},
        'daily':{
            'time':['2026-08-13','2026-08-14'],
            'precipitation_probability_max':[30,85],
            'precipitation_sum':[2,24],
            'temperature_2m_max':[32,31],
            'temperature_2m_min':[24,24],
        }
    }
    out = build_weather_decision_context(weather, 'Can I apply fertilizer tomorrow?')
    codes = {x['code'] for x in out['risk_flags']}
    assert out['decision_usable'] is True
    assert out['operation'] == 'fertilizer_application'
    assert 'high_rain_probability' in codes
    assert 'fertilizer_weather_loss_risk' in codes

    fallback = build_weather_decision_context({'status':'fallback_demo','live':False,'source':'demo-fallback','current':{},'daily':{}}, 'weather now')
    assert fallback['decision_usable'] is False
    assert any(x['code'] == 'live_weather_unavailable' for x in fallback['risk_flags'])
    print('MihiMura Phase 3 weather-decision test: PASS')


if __name__ == '__main__':
    main()
