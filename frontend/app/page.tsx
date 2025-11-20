'use client';

import { useEffect, useState } from 'react';
import { AlertCircle, Package, TrendingDown, Clock } from 'lucide-react';
import Navbar from '@/components/Navbar';
import StatsCard from '@/components/StatsCard';
import NotificationBell from '@/components/NotificationBell';
import { dashboardApi, invoiceApi, DashboardSummary, Invoice } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';
import { tr } from 'date-fns/locale';

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recentInvoices, setRecentInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      const [summaryData, invoicesData] = await Promise.all([
        dashboardApi.getSummary(),
        invoiceApi.getRecent(10),
      ]);
      setSummary(summaryData);
      setRecentInvoices(invoicesData);
    } catch (error) {
      console.error('Dashboard yüklenemedi:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <>
        <Navbar />
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
            <p className="mt-4 text-gray-600">Yükleniyor...</p>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-gray-600 mt-1">Stok durumu ve uyarılar</p>
          </div>
          <NotificationBell />
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatsCard
            title="SKT Yaklaşan (7 gün)"
            value={summary?.expiry_count || 0}
            subtitle="Ürün"
            icon={Clock}
            variant={summary && summary.expiry_count > 0 ? 'danger' : 'success'}
          />
          <StatsCard
            title="Stok Azalan"
            value={summary?.low_stock_count || 0}
            subtitle="Ürün"
            icon={TrendingDown}
            variant={summary && summary.low_stock_count > 0 ? 'warning' : 'success'}
          />
          <StatsCard
            title="Toplam Fatura"
            value={recentInvoices.length}
            subtitle="Son 30 gün"
            icon={Package}
            variant="default"
          />
        </div>

        {/* Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Invoices */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">
                Son Faturalar
              </h2>
              <a
                href="/upload"
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                Yeni Yükle
              </a>
            </div>
            <div className="space-y-3">
              {recentInvoices.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-8">
                  Henüz fatura yüklenmedi
                </p>
              ) : (
                recentInvoices.slice(0, 5).map((invoice) => (
                  <div
                    key={invoice.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <Package className="w-5 h-5 text-blue-600" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          Fatura #{invoice.id}
                        </p>
                        <p className="text-xs text-gray-500">
                          {invoice.created_at &&
                            formatDistanceToNow(new Date(invoice.created_at), {
                              addSuffix: true,
                              locale: tr,
                            })}
                        </p>
                      </div>
                    </div>
                    <a
                      href={`/invoices/${invoice.id}`}
                      className="text-sm text-blue-600 hover:text-blue-700"
                    >
                      Detay
                    </a>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Hızlı İşlemler
            </h2>
            <div className="space-y-3">
              <a
                href="/upload"
                className="flex items-center gap-3 p-4 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors group"
              >
                <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                  <Package className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900 group-hover:text-blue-700">
                    Fiş Yükle
                  </p>
                  <p className="text-xs text-gray-500">
                    OCR ile otomatik tarama
                  </p>
                </div>
              </a>
              <a
                href="/products"
                className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
              >
                <div className="w-10 h-10 bg-gray-600 rounded-lg flex items-center justify-center">
                  <AlertCircle className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900 group-hover:text-gray-700">
                    Ürün Yönetimi
                  </p>
                  <p className="text-xs text-gray-500">
                    Ürün ekle, düzenle, sil
                  </p>
                </div>
              </a>
              <a
                href="/alerts"
                className="flex items-center gap-3 p-4 bg-red-50 rounded-lg hover:bg-red-100 transition-colors group"
              >
                <div className="w-10 h-10 bg-red-600 rounded-lg flex items-center justify-center">
                  <Clock className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900 group-hover:text-red-700">
                    SKT Uyarıları
                  </p>
                  <p className="text-xs text-gray-500">
                    {summary?.expiry_count || 0} kritik ürün
                  </p>
                </div>
              </a>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
