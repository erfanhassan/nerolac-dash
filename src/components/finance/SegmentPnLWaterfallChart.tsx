'use client';

import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

export interface WaterfallDataPoint {
  name: string;
  value: number;
  is_intermediate: boolean;
  is_negative: boolean;
}

interface SegmentPnLWaterfallChartProps {
  data: WaterfallDataPoint[];
  isLoading?: boolean;
}

export function SegmentPnLWaterfallChart({
  data,
  isLoading = false,
}: SegmentPnLWaterfallChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current || !data || data.length === 0) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    // Build waterfall base offset and value bars
    const categories: string[] = [];
    const baseOffset: number[] = [];
    const barValues: number[] = [];
    const barColors: string[] = [];

    let currentAccumulator = 0;

    data.forEach((item) => {
      categories.push(item.name);

      if (item.is_intermediate) {
        // Milestone subtotal (Net Revenue, Gross Margin, EBITDA, Net Profit)
        baseOffset.push(0);
        barValues.push(item.value);
        currentAccumulator = item.value;
        barColors.push(item.value >= 0 ? '#059669' : '#D32F2F');
      } else if (item.is_negative) {
        // Expense deduction
        const absVal = Math.abs(item.value);
        currentAccumulator -= absVal;
        baseOffset.push(Math.max(0, currentAccumulator));
        barValues.push(absVal);
        barColors.push('#D32F2F'); // Nerolac Red for deductions
      } else {
        // Positive inflow/revenue
        baseOffset.push(currentAccumulator);
        barValues.push(item.value);
        currentAccumulator += item.value;
        barColors.push('#1E3A8A'); // Corporate Navy
      }
    });

    const option: echarts.EChartsOption = {
      backgroundColor: '#FFFFFF',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const tar = params[1] || params[0];
          const rawItem = data[tar.dataIndex];
          const valFormatted = new Intl.NumberFormat('en-BD', {
            style: 'currency',
            currency: 'BDT',
            maximumFractionDigits: 0,
          }).format(rawItem ? rawItem.value : tar.value);
          return `<div style="font-family: inherit; font-size: 12px; font-variant-numeric: tabular-nums;">
            <strong>${tar.name}</strong><br/>
            Amount: <span style="font-weight: 600; color: #0F172A;">${valFormatted}</span>
          </div>`;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '12%',
        top: '8%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: {
          interval: 0,
          rotate: 25,
          fontSize: 11,
          color: '#334155',
          fontFamily: 'inherit',
        },
        axisLine: { lineStyle: { color: '#CBD5E1' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (value: number) => `৳${(value / 1000000).toFixed(1)}M`,
          fontSize: 11,
          color: '#64748B',
          fontFamily: 'inherit',
        },
        splitLine: {
          lineStyle: {
            color: '#E2E8F0',
            type: 'dashed',
          },
        },
      },
      series: [
        {
          name: 'Offset',
          type: 'bar',
          stack: 'Total',
          itemStyle: {
            borderColor: 'transparent',
            color: 'transparent',
          },
          emphasis: {
            itemStyle: {
              borderColor: 'transparent',
              color: 'transparent',
            },
          },
          data: baseOffset,
        },
        {
          name: 'P&L Amount',
          type: 'bar',
          stack: 'Total',
          label: {
            show: true,
            position: 'top',
            fontSize: 10,
            color: '#475569',
            formatter: (params: any) => {
              const raw = data[params.dataIndex];
              const v = raw ? raw.value : params.value;
              return `৳${(v / 1000000).toFixed(1)}M`;
            },
          },
          itemStyle: {
            color: (params: any) => barColors[params.dataIndex] || '#475569',
            borderRadius: [2, 2, 0, 0],
          },
          data: barValues,
        },
      ],
    };

    chartInstance.current.setOption(option);

    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [data]);

  return (
    <div
      style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '6px',
        padding: '16px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '12px',
        }}
      >
        <div>
          <h3
            style={{
              fontSize: '14px',
              fontWeight: 700,
              color: '#0F172A',
              letterSpacing: '0.2px',
            }}
          >
            Segment P&L Waterfall
          </h3>
          <p style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
            GL 10000–10017 Margin Progression (Gross Sales → Net Revenue → COGS → EBITDA → Net
            Profit)
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', fontSize: '11px', fontWeight: 600 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#1E3A8A' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                backgroundColor: '#1E3A8A',
                borderRadius: '1px',
              }}
            />
            Revenue Inflow
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#D32F2F' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                backgroundColor: '#D32F2F',
                borderRadius: '1px',
              }}
            />
            Cost Deduction
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#059669' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                backgroundColor: '#059669',
                borderRadius: '1px',
              }}
            />
            Subtotal Milestone
          </span>
        </div>
      </div>

      <div
        id="echarts-waterfall-container"
        ref={chartRef}
        style={{ width: '100%', height: '320px', minHeight: '320px' }}
      />
    </div>
  );
}
