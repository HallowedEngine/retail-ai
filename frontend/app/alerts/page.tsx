'use client';

import { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, Clock, XCircle } from 'lucide-react';
import Navbar from '@/components/Navbar';
import { alertApi, ExpiryAlert } from '@/lib/api';
import clsx from 'clsx';
import { format } from 'date-fns';
import { tr } from 'date-fns/locale';

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<ExpiryAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'critical' | 'warning'>('all');

  useEffect(() => {
    loadAlerts();
  }, []);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      const data = await alertApi.getExpiry(1, 30);
      setAlerts(data);
    } catch (error) {
      console.error('Uyarılar yüklenemedi:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async (alertId: number) => {
    try {
      await alertApi.acknowledge(alertId);
      await loadAlerts();
    } catch (error) {
      console.error('Uyarı onaylanamadı:', error);
    }
  };

  const handleSnooze = async (alertId: number, days: number) => {
    try {
      await alertApi.snooze(alertId, days);
      await loadAlerts();
    } catch (error) {
      console.error('Uyarı ertelenemedi:', error);
    }
  };

  const filteredAlerts = alerts.filter((alert) => {
    if (filter === 'critical') return alert.severity === 'red';
    if (filter === 'warning') return alert.severity === 'yellow';
    return true;
  });

  const criticalCount = alerts.filter((a) => a.severity === 'red').length;
  const warningCount = alerts.filter((a) => a.severity === 'yellow').length;

  return (
    <>
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">SKT Uyarıları</h1>
          <p className="text-gray-600 mt-1">
            {criticalCount} kritik, {warningCount} uyarı
          </p>
        </div>

        {/* Filter Tabs */}
        <div className="mb-6 flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={clsx(
              'px-4 py-2 rounded-lg font-medium transition-colors',
              filter === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
            )}
          >
            Tümü ({alerts.length})
          </button>
          <button
            onClick={() => setFilter('critical')}
            className={clsx(
              'px-4 py-2 rounded-lg font-medium transition-colors',
              filter === 'critical'
                ? 'bg-red-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
            )}
          >
            Kritik ({criticalCount})
          </button>
          <button
            onClick={() => setFilter('warning')}
            className={clsx(
              'px-4 py-2 rounded-lg font-medium transition-colors',
              filter === 'warning'
                ? 'bg-yellow-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
            )}
          >
            Uyarı ({warningCount})
          </button>
        </div>

        {/* Alerts List */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow-sm border border-gray-200">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <p className="text-gray-600 font-medium">Harika! Aktif uyarı yok</p>
            <p className="text-sm text-gray-500 mt-2">
              Tüm ürünler SKT açısından güvende
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredAlerts.map((alert) => (
              <div
                key={alert.id}
                className={clsx(
                  'bg-white rounded-lg shadow-sm border p-4',
                  alert.severity === 'red'
                    ? 'border-red-200 bg-red-50'
                    : 'border-yellow-200 bg-yellow-50',
                  alert.status === 'ack' && 'opacity-50'
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    {/* Icon */}
                    <div
                      className={clsx(
                        'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
                        alert.severity === 'red'
                          ? 'bg-red-100'
                          : 'bg-yellow-100'
                      )}
                    >
                      {alert.severity === 'red' ? (
                        <XCircle className="w-6 h-6 text-red-600" />
                      ) : (
                        <AlertCircle className="w-6 h-6 text-yellow-600" />
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-gray-900">
                          Ürün #{alert.product_id} - Batch #{alert.batch_id}
                        </h3>
                        <span
                          className={clsx(
                            'text-xs px-2 py-1 rounded-full font-medium',
                            alert.severity === 'red'
                              ? 'bg-red-200 text-red-800'
                              : 'bg-yellow-200 text-yellow-800'
                          )}
                        >
                          {alert.days_left} gün kaldı
                        </span>
                      </div>
                      <div className="text-sm text-gray-600 space-y-1">
                        <p>
                          <Clock className="w-4 h-4 inline mr-1" />
                          SKT: {format(new Date(alert.expiry_date), 'dd MMMM yyyy', { locale: tr })}
                        </p>
                        {alert.status === 'ack' && (
                          <p className="text-green-600 font-medium">
                            ✓ Onaylandı
                          </p>
                        )}
                        {alert.status === 'snoozed' && alert.snooze_until && (
                          <p className="text-blue-600 font-medium">
                            ⏰ {format(new Date(alert.snooze_until), 'dd MMMM', { locale: tr })} tarihine kadar ertelendi
                          </p>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  {alert.status !== 'ack' && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleSnooze(alert.id, 1)}
                        className="px-3 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                        title="1 gün ertele"
                      >
                        Ertele
                      </button>
                      <button
                        onClick={() => handleAcknowledge(alert.id)}
                        className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
                      >
                        Onayla
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
