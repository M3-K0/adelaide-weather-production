'use client';

import React from 'react';
import { CAPEBadge } from './CAPEBadge';

/**
 * Example usage of the CAPE Badge component
 * This demonstrates various configurations and use cases
 */
export const CAPEBadgeExample: React.FC = () => {
  const exampleValues = [
    { value: 250, percentile: 35, season: 'Winter', label: 'Low Risk Example' },
    {
      value: 750,
      percentile: 65,
      season: 'Spring',
      label: 'Moderate Risk Example'
    },
    {
      value: 1500,
      percentile: 85,
      season: 'Summer',
      label: 'High Risk Example'
    },
    {
      value: 3000,
      percentile: 95,
      season: 'Summer',
      label: 'Extreme Risk Example'
    }
  ];

  return (
    <div className='space-y-8 p-6 bg-[#0A0D12] min-h-screen'>
      <div className='max-w-4xl mx-auto space-y-6'>
        <h1 className='text-2xl font-bold text-slate-50 mb-6'>
          CAPE Risk Badge Examples
        </h1>

        {/* Basic Examples */}
        <section className='space-y-4'>
          <h2 className='text-lg font-semibold text-slate-200'>Risk Levels</h2>
          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
            {exampleValues.map(example => (
              <div
                key={example.value}
                className='bg-[#0E1116] border border-[#2A2F3A] rounded-lg p-4 space-y-3'
              >
                <h3 className='text-sm font-medium text-slate-300'>
                  {example.label}
                </h3>
                <CAPEBadge
                  value={example.value}
                  percentile={example.percentile}
                  season={example.season}
                />
                <div className='text-xs text-slate-500 space-y-1'>
                  <div>Value: {example.value.toLocaleString()} J/kg</div>
                  <div>
                    Percentile: {example.percentile}% ({example.season})
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Size Variants */}
        <section className='space-y-4'>
          <h2 className='text-lg font-semibold text-slate-200'>
            Size Variants
          </h2>
          <div className='bg-[#0E1116] border border-[#2A2F3A] rounded-lg p-6 space-y-4'>
            <div className='flex items-center gap-4 flex-wrap'>
              <div className='space-y-2'>
                <div className='text-xs text-slate-400'>Small</div>
                <CAPEBadge value={1500} size='sm' />
              </div>
              <div className='space-y-2'>
                <div className='text-xs text-slate-400'>Medium (Default)</div>
                <CAPEBadge value={1500} size='md' />
              </div>
              <div className='space-y-2'>
                <div className='text-xs text-slate-400'>Large</div>
                <CAPEBadge value={1500} size='lg' />
              </div>
            </div>
          </div>
        </section>

        {/* Configuration Options */}
        <section className='space-y-4'>
          <h2 className='text-lg font-semibold text-slate-200'>
            Configuration Options
          </h2>
          <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
            <div className='bg-[#0E1116] border border-[#2A2F3A] rounded-lg p-4 space-y-3'>
              <h3 className='text-sm font-medium text-slate-300'>
                With Info Modal
              </h3>
              <CAPEBadge
                value={2500}
                percentile={92}
                season='Summer'
                showInfo={true}
              />
              <p className='text-xs text-slate-500'>
                Click to see detailed explanation
              </p>
            </div>

            <div className='bg-[#0E1116] border border-[#2A2F3A] rounded-lg p-4 space-y-3'>
              <h3 className='text-sm font-medium text-slate-300'>
                Without Info Modal
              </h3>
              <CAPEBadge value={2500} showInfo={false} />
              <p className='text-xs text-slate-500'>Static display only</p>
            </div>

            <div className='bg-[#0E1116] border border-[#2A2F3A] rounded-lg p-4 space-y-3'>
              <h3 className='text-sm font-medium text-slate-300'>
                No Historical Data
              </h3>
              <CAPEBadge value={1200} />
              <p className='text-xs text-slate-500'>
                Without percentile information
              </p>
            </div>

            <div className='bg-[#0E1116] border border-[#2A2F3A] rounded-lg p-4 space-y-3'>
              <h3 className='text-sm font-medium text-slate-300'>
                Extreme with Animation
              </h3>
              <CAPEBadge value={3500} percentile={98} season='Summer' />
              <p className='text-xs text-slate-500'>
                Lightning animation for extreme levels
              </p>
            </div>
          </div>
        </section>

        {/* Integration Examples */}
        <section className='space-y-4'>
          <h2 className='text-lg font-semibold text-slate-200'>
            Integration Examples
          </h2>

          {/* In a forecast card */}
          <div className='bg-[#0E1116] border border-[#2A2F3A] rounded-lg p-6 space-y-4'>
            <h3 className='text-sm font-medium text-slate-300'>
              Forecast Card Integration
            </h3>
            <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
              <div className='space-y-3'>
                <div className='flex items-center justify-between'>
                  <span className='text-slate-300'>Temperature</span>
                  <span className='text-2xl font-light text-slate-50'>
                    24.5°C
                  </span>
                </div>
                <div className='flex items-center justify-between'>
                  <span className='text-slate-400'>Convective Risk</span>
                  <CAPEBadge
                    value={1800}
                    percentile={88}
                    season='Summer'
                    size='sm'
                  />
                </div>
                <div className='text-xs text-slate-500'>
                  High risk of thunderstorm development
                </div>
              </div>

              <div className='space-y-3'>
                <div className='flex items-center justify-between'>
                  <span className='text-slate-300'>Temperature</span>
                  <span className='text-2xl font-light text-slate-50'>
                    16.2°C
                  </span>
                </div>
                <div className='flex items-center justify-between'>
                  <span className='text-slate-400'>Convective Risk</span>
                  <CAPEBadge
                    value={320}
                    percentile={42}
                    season='Autumn'
                    size='sm'
                  />
                </div>
                <div className='text-xs text-slate-500'>
                  Stable conditions expected
                </div>
              </div>
            </div>
          </div>

          {/* In a data table */}
          <div className='bg-[#0E1116] border border-[#2A2F3A] rounded-lg overflow-hidden'>
            <h3 className='text-sm font-medium text-slate-300 p-4 border-b border-[#2A2F3A]'>
              Hourly Forecast Table
            </h3>
            <div className='overflow-x-auto'>
              <table className='w-full text-sm'>
                <thead className='bg-[#1C1F26]'>
                  <tr>
                    <th className='text-left p-3 text-slate-400'>Time</th>
                    <th className='text-left p-3 text-slate-400'>Temp</th>
                    <th className='text-left p-3 text-slate-400'>CAPE Risk</th>
                    <th className='text-left p-3 text-slate-400'>Conditions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className='border-b border-[#2A2F3A]'>
                    <td className='p-3 text-slate-300'>12:00</td>
                    <td className='p-3 text-slate-200'>22.1°C</td>
                    <td className='p-3'>
                      <CAPEBadge value={1250} size='sm' />
                    </td>
                    <td className='p-3 text-slate-400'>Partly cloudy</td>
                  </tr>
                  <tr className='border-b border-[#2A2F3A]'>
                    <td className='p-3 text-slate-300'>15:00</td>
                    <td className='p-3 text-slate-200'>26.8°C</td>
                    <td className='p-3'>
                      <CAPEBadge value={2100} size='sm' />
                    </td>
                    <td className='p-3 text-slate-400'>Thunderstorms likely</td>
                  </tr>
                  <tr>
                    <td className='p-3 text-slate-300'>18:00</td>
                    <td className='p-3 text-slate-200'>19.4°C</td>
                    <td className='p-3'>
                      <CAPEBadge value={450} size='sm' />
                    </td>
                    <td className='p-3 text-slate-400'>Clear skies</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Edge Cases */}
        <section className='space-y-4'>
          <h2 className='text-lg font-semibold text-slate-200'>Edge Cases</h2>
          <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
            <div className='bg-[#0E1116] border border-[#2A2F3A] rounded-lg p-4 space-y-3'>
              <h3 className='text-sm font-medium text-slate-300'>Zero CAPE</h3>
              <CAPEBadge value={0} />
              <p className='text-xs text-slate-500'>
                Completely stable conditions
              </p>
            </div>

            <div className='bg-[#0E1116] border border-[#2A2F3A] rounded-lg p-4 space-y-3'>
              <h3 className='text-sm font-medium text-slate-300'>
                Boundary Values
              </h3>
              <div className='space-y-2'>
                <CAPEBadge value={500} size='sm' />
                <CAPEBadge value={1000} size='sm' />
                <CAPEBadge value={2000} size='sm' />
              </div>
              <p className='text-xs text-slate-500'>
                Exact threshold boundaries
              </p>
            </div>

            <div className='bg-[#0E1116] border border-[#2A2F3A] rounded-lg p-4 space-y-3'>
              <h3 className='text-sm font-medium text-slate-300'>
                Very High Values
              </h3>
              <CAPEBadge value={10000} />
              <p className='text-xs text-slate-500'>
                Exceptional atmospheric instability
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default CAPEBadgeExample;
