'use client';

import { useState, useEffect } from 'react';
import { Bell } from 'lucide-react';
import { alertApi, ExpiryAlert } from '@/lib/api';
import clsx from 'clsx';

export default function NotificationBell() {
  const [alerts, setAlerts] = useState<ExpiryAlert[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    loadAlerts();
    const interval = setInterval(loadAlerts, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadAlerts = async () => {
    try {
      const data = await alertApi.getExpiry(1, 7);
      const newAlerts = data.filter(a => a.status !== 'ack');
      setAlerts(newAlerts);
      setUnreadCount(newAlerts.length);
    } catch (error) {
      console.error('Failed to load alerts:', error);
    }
  };

  const criticalAlerts = alerts.filter(a => a.days_left <= 3);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-600 hover:text-gray-900 focus:outline-none"
      >
        <Bell className="w-6 h-6" />
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-red-600 rounded-full">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 z-20 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
            <div className="p-4 border-b border-gray-200">
              <h3 className="text-sm font-semibold text-gray-900">
                Bildirimler
              </h3>
              <p className="text-xs text-gray-500 mt-1">
                {unreadCount} yeni uyarı
              </p>
            </div>
            <div className="max-h-96 overflow-y-auto">
              {alerts.length === 0 ? (
                <div className="p-4 text-sm text-gray-500 text-center">
                  Yeni bildirim yok
                </div>
              ) : (
                alerts.slice(0, 10).map((alert) => (
                  <div
                    key={alert.id}
                    className={clsx(
                      'p-4 border-b border-gray-100 hover:bg-gray-50 cursor-pointer',
                      alert.days_left <= 3 && 'bg-red-50'
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">
                          SKT Uyarısı - Ürün #{alert.product_id}
                        </p>
                        <p className="text-xs text-gray-600 mt-1">
                          {alert.days_left} gün kaldı
                        </p>
                      </div>
                      <span
                        className={clsx(
                          'text-xs px-2 py-1 rounded-full',
                          alert.severity === 'red'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-yellow-100 text-yellow-700'
                        )}
                      >
                        {alert.severity === 'red' ? 'Kritik' : 'Uyarı'}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
            {alerts.length > 0 && (
              <div className="p-3 bg-gray-50 text-center">
                <a
                  href="/alerts"
                  className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                  onClick={() => setIsOpen(false)}
                >
                  Tüm uyarıları gör
                </a>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
