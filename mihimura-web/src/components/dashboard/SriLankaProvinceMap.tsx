import { Minus, Plus, RotateCcw } from 'lucide-react';
import { useMemo, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { sriLankaDistricts } from '../../data/sriLankaDistricts';
import { provinceLabelPositions } from '../../data/mockApi';
import type { MapLayer, ProvinceData, RiskLevel } from '../../data/mockApi';

interface SriLankaProvinceMapProps {
  selectedProvince: string;
  activeLayer: MapLayer;
  provinces: Record<string, ProvinceData>;
  onSelectProvince: (province: string) => void;
}

export const getLayerValue = (province: string, layer: MapLayer, provinces: Record<string, ProvinceData>) => {
  const data = provinces[province];
  if (!data) return 0;
  if (layer === 'cropHealth') return data.healthScore;
  if (layer === 'rainfallRisk') return data.rainfallRisk;
  return data.pestRisk;
};

export const getLayerRiskLevel = (value: number, layer: MapLayer): RiskLevel => {
  if (layer === 'cropHealth') {
    if (value >= 80) return 'Healthy';
    if (value >= 60) return 'Watch';
    if (value >= 40) return 'Moderate Risk';
    return 'High Risk';
  }

  if (value <= 25) return 'Healthy';
  if (value <= 45) return 'Watch';
  if (value <= 70) return 'Moderate Risk';
  return 'High Risk';
};

export const getRiskColor = (risk: RiskLevel) => {
  if (risk === 'Healthy') return '#2f7d4a';
  if (risk === 'Watch') return '#d6b64c';
  if (risk === 'Moderate Risk') return '#ed9637';
  return '#d9554f';
};

export function SriLankaProvinceMap({ selectedProvince, activeLayer, provinces, onSelectProvince }: SriLankaProvinceMapProps) {
  const [zoom, setZoom] = useState(1);
  const [hoveredProvince, setHoveredProvince] = useState<string | null>(null);

  const provinceColors = useMemo(() => {
    return Object.fromEntries(
      Object.keys(provinces).map((province) => {
        const value = getLayerValue(province, activeLayer, provinces);
        return [province, getRiskColor(getLayerRiskLevel(value, activeLayer))];
      }),
    );
  }, [activeLayer, provinces]);

  const visibleProvince = hoveredProvince ?? selectedProvince;
  const visibleValue = getLayerValue(visibleProvince, activeLayer, provinces);

  return (
    <div className="province-map-shell">
      <div className="map-zoom-controls" aria-label="Map zoom controls">
        <button type="button" onClick={() => setZoom((value) => Math.min(1.45, value + 0.1))} aria-label="Zoom in">
          <Plus size={17} />
        </button>
        <button type="button" onClick={() => setZoom((value) => Math.max(0.88, value - 0.1))} aria-label="Zoom out">
          <Minus size={17} />
        </button>
        <button type="button" onClick={() => setZoom(1)} aria-label="Reset map zoom">
          <RotateCcw size={16} />
        </button>
      </div>

      <div className="map-hover-readout">
        <span>{visibleProvince} Province</span>
        <strong>{visibleValue}/100</strong>
      </div>

      <svg className="province-map" viewBox="0 0 450 793" role="img" aria-label="Sri Lanka provincial agricultural risk map">
        <defs>
          <filter id="selectedProvinceGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#143f28" floodOpacity="0.26" />
          </filter>
        </defs>
        <g className="province-map__geometry" style={{ transform: `scale(${zoom})`, transformOrigin: '225px 396.5px' }}>
          {sriLankaDistricts.map((district) => {
            const isSelected = district.province === selectedProvince;
            const isHovered = district.province === hoveredProvince;
            return (
              <path
                key={district.id}
                d={district.path}
                fill={provinceColors[district.province] ?? '#dfe8df'}
                className={`district-shape${isSelected ? ' is-selected' : ''}${isHovered ? ' is-hovered' : ''}`}
                style={{ filter: isSelected ? 'url(#selectedProvinceGlow)' : undefined }}
                onClick={() => onSelectProvince(district.province)}
                onMouseEnter={() => setHoveredProvince(district.province)}
                onMouseLeave={() => setHoveredProvince(null)}
                aria-label={`${district.name} District, ${district.province} Province`}
              />
            );
          })}

          {Object.entries(provinceLabelPositions).map(([province, label]) => {
            const selected = province === selectedProvince;
            return (
              <g
                key={province}
                className={`province-label${selected ? ' is-selected' : ''}`}
                onClick={() => onSelectProvince(province)}
                role="button"
                tabIndex={0}
                onKeyDown={(event: KeyboardEvent<SVGGElement>) => {
                  if (event.key === 'Enter' || event.key === ' ') onSelectProvince(province);
                }}
              >
                <rect x={label.x - 42} y={label.y - 13} width="84" height="26" rx="13" />
                <text x={label.x} y={label.y + 4} textAnchor="middle">{label.short}</text>
              </g>
            );
          })}
        </g>
      </svg>

      <div className="map-source-note">District geometry grouped into 9 official provinces</div>
    </div>
  );
}
