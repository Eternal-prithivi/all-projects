/**
 * Utility functions for exporting data to CSV and PDF formats
 */

import jsPDF from 'jspdf';
import 'jspdf-autotable';

/**
 * Convert array of objects to CSV format
 * @param {Array} data - Array of objects to convert
 * @param {Array} headers - Optional array of header names
 * @returns {string} CSV formatted string
 */
export const convertToCSV = (data, headers = null) => {
  if (!data || data.length === 0) {
    return '';
  }

  // Get headers from first object if not provided
  const csvHeaders = headers || Object.keys(data[0]);
  
  // Create header row
  const headerRow = csvHeaders.join(',');
  
  // Create data rows
  const dataRows = data.map(item => {
    return csvHeaders.map(header => {
      let value = item[header] || '';
      
      // Handle nested objects and arrays
      if (typeof value === 'object' && value !== null) {
        value = JSON.stringify(value);
      }
      
      // Escape quotes and wrap in quotes if contains comma or newline
      value = String(value).replace(/"/g, '""');
      if (value.includes(',') || value.includes('\n') || value.includes('"')) {
        value = `"${value}"`;
      }
      
      return value;
    }).join(',');
  });
  
  return [headerRow, ...dataRows].join('\n');
};

/**
 * Download CSV file
 * @param {string} csvContent - CSV formatted string
 * @param {string} filename - Name of the file to download
 */
export const downloadCSV = (csvContent, filename = 'export.csv') => {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  
  if (link.download !== undefined) {
    // Create download link
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    
    // Trigger download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Clean up
    URL.revokeObjectURL(url);
  }
};

/**
 * Export data to CSV file
 * @param {Array} data - Array of objects to export
 * @param {string} filename - Name of the file
 * @param {Array} headers - Optional custom headers
 */
export const exportToCSV = (data, filename = 'export.csv', headers = null) => {
  const csvContent = convertToCSV(data, headers);
  downloadCSV(csvContent, filename);
};

/**
 * Format date for export
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date string
 */
export const formatDateForExport = (date) => {
  if (!date) return '';
  
  const d = new Date(date);
  if (isNaN(d.getTime())) return '';
  
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

/**
 * Format currency for export
 * @param {number} amount - Amount to format
 * @param {string} currency - Currency code
 * @returns {string} Formatted currency string
 */
export const formatCurrencyForExport = (amount, currency = 'INR') => {
  if (amount === null || amount === undefined) return '';
  
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: currency
  }).format(amount);
};

/**
 * Prepare users data for CSV export
 * @param {Array} users - Array of user objects
 * @returns {Array} Formatted data for export
 */
export const prepareUsersForExport = (users) => {
  return users.map(user => ({
    'Username': user.username || '',
    'Email': user.email || '',
    'Role': user.role || 'user',
    'Status': user.status || 'active',
    'Account Created': formatDateForExport(user.created_at),
    'Last Login': formatDateForExport(user.last_login),
    '2FA Enabled': user.totp_secret ? 'Yes' : 'No',
    'Active Sessions': user.active_sessions || 0
  }));
};

/**
 * Prepare analytics data for CSV export
 * @param {Object} analytics - Analytics object
 * @returns {Array} Formatted data for export
 */
export const prepareAnalyticsForExport = (analytics) => {
  const data = [];
  
  // User metrics
  data.push({
    'Metric': 'Total Users',
    'Value': analytics.total_users || 0,
    'Change': analytics.user_growth || '0%',
    'Category': 'Users'
  });
  
  data.push({
    'Metric': 'Active Users',
    'Value': analytics.active_users || 0,
    'Change': analytics.active_growth || '0%',
    'Category': 'Users'
  });
  
  // Revenue metrics
  data.push({
    'Metric': 'Total Revenue',
    'Value': formatCurrencyForExport(analytics.total_revenue),
    'Change': analytics.revenue_growth || '0%',
    'Category': 'Revenue'
  });
  
  data.push({
    'Metric': 'Monthly Recurring Revenue',
    'Value': formatCurrencyForExport(analytics.mrr),
    'Change': analytics.mrr_growth || '0%',
    'Category': 'Revenue'
  });
  
  // VM metrics
  data.push({
    'Metric': 'Total VMs',
    'Value': analytics.total_vms || 0,
    'Change': '',
    'Category': 'Resources'
  });
  
  data.push({
    'Metric': 'Active VMs',
    'Value': analytics.active_vms || 0,
    'Change': '',
    'Category': 'Resources'
  });
  
  return data;
};

/**
 * Prepare payments data for CSV export
 * @param {Array} payments - Array of payment objects
 * @returns {Array} Formatted data for export
 */
export const preparePaymentsForExport = (payments) => {
  return payments.map(payment => ({
    'Payment ID': payment.razorpay_payment_id || payment._id || '',
    'Username': payment.username || '',
    'Plan': payment.plan_name || '',
    'Amount': formatCurrencyForExport(payment.amount / 100, payment.currency || 'INR'),
    'Status': payment.status || '',
    'Payment Method': payment.method || '',
    'Date': formatDateForExport(payment.created_at || payment.payment_date),
    'Subscription ID': payment.razorpay_subscription_id || ''
  }));
};

/**
 * Export users data to PDF
 * @param {Array} users - Array of user objects
 * @param {string} filename - Name of the PDF file
 */
export const exportUsersToPDF = (users, filename = 'users_report.pdf') => {
  const doc = new jsPDF();
  
  // Add title
  doc.setFontSize(20);
  doc.setTextColor(99, 102, 241); // Purple
  doc.text('User Management Report', 14, 22);
  
  // Add date
  doc.setFontSize(10);
  doc.setTextColor(128, 128, 128);
  doc.text(`Generated: ${new Date().toLocaleDateString()}`, 14, 30);
  
  // Prepare table data
  const tableData = users.map(user => [
    user.username || '',
    user.email || '',
    user.role || 'user',
    user.status || 'active',
    formatDateForExport(user.created_at),
    user.totp_secret ? 'Yes' : 'No'
  ]);
  
  // Add table
  doc.autoTable({
    head: [['Username', 'Email', 'Role', 'Status', 'Joined', '2FA']],
    body: tableData,
    startY: 35,
    theme: 'grid',
    headStyles: { fillColor: [99, 102, 241], textColor: 255 },
    styles: { fontSize: 9 },
    alternateRowStyles: { fillColor: [245, 245, 245] }
  });
  
  // Add footer
  const pageCount = doc.internal.getNumberOfPages();
  doc.setFontSize(8);
  doc.setTextColor(128, 128, 128);
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.text(`Page ${i} of ${pageCount}`, doc.internal.pageSize.getWidth() - 30, doc.internal.pageSize.getHeight() - 10);
  }
  
  // Save
  doc.save(filename);
};

/**
 * Export analytics data to PDF
 * @param {Object} analytics - Analytics object
 * @param {string} filename - Name of the PDF file
 */
export const exportAnalyticsToPDF = (analytics, filename = 'analytics_report.pdf') => {
  const doc = new jsPDF();
  
  // Add title
  doc.setFontSize(20);
  doc.setTextColor(99, 102, 241);
  doc.text('Platform Analytics Report', 14, 22);
  
  // Add date
  doc.setFontSize(10);
  doc.setTextColor(128, 128, 128);
  doc.text(`Generated: ${new Date().toLocaleDateString()}`, 14, 30);
  
  // User Metrics
  doc.setFontSize(14);
  doc.setTextColor(0, 0, 0);
  doc.text('User Metrics', 14, 45);
  
  doc.autoTable({
    head: [['Metric', 'Value', 'Growth']],
    body: [
      ['Total Users', analytics.total_users || 0, analytics.user_growth || '0%'],
      ['Active Users', analytics.active_users || 0, analytics.active_growth || '0%']
    ],
    startY: 50,
    theme: 'striped',
    headStyles: { fillColor: [99, 102, 241] }
  });
  
  // Revenue Metrics
  const finalY = doc.lastAutoTable.finalY + 10;
  doc.setFontSize(14);
  doc.text('Revenue Metrics', 14, finalY);
  
  doc.autoTable({
    head: [['Metric', 'Value', 'Growth']],
    body: [
      ['Total Revenue', formatCurrencyForExport(analytics.total_revenue), analytics.revenue_growth || '0%'],
      ['MRR', formatCurrencyForExport(analytics.mrr), analytics.mrr_growth || '0%']
    ],
    startY: finalY + 5,
    theme: 'striped',
    headStyles: { fillColor: [212, 175, 55] } // Gold
  });
  
  // Resource Metrics
  const finalY2 = doc.lastAutoTable.finalY + 10;
  doc.setFontSize(14);
  doc.text('Resource Metrics', 14, finalY2);
  
  doc.autoTable({
    head: [['Metric', 'Value']],
    body: [
      ['Total VMs', analytics.total_vms || 0],
      ['Active VMs', analytics.active_vms || 0],
      ['Total Storage (GB)', analytics.total_storage || 0]
    ],
    startY: finalY2 + 5,
    theme: 'striped',
    headStyles: { fillColor: [139, 92, 246] } // Purple
  });
  
  // Add footer
  const pageCount = doc.internal.getNumberOfPages();
  doc.setFontSize(8);
  doc.setTextColor(128, 128, 128);
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.text(`Page ${i} of ${pageCount}`, doc.internal.pageSize.getWidth() - 30, doc.internal.pageSize.getHeight() - 10);
  }
  
  doc.save(filename);
};

/**
 * Export payments data to PDF
 * @param {Array} payments - Array of payment objects
 * @param {Object} stats - Payment statistics
 * @param {string} filename - Name of the PDF file
 */
export const exportPaymentsToPDF = (payments, stats = {}, filename = 'payments_report.pdf') => {
  const doc = new jsPDF();
  
  // Add title
  doc.setFontSize(20);
  doc.setTextColor(99, 102, 241);
  doc.text('Payment Transactions Report', 14, 22);
  
  // Add date and summary
  doc.setFontSize(10);
  doc.setTextColor(128, 128, 128);
  doc.text(`Generated: ${new Date().toLocaleDateString()}`, 14, 30);
  doc.text(`Total Transactions: ${stats.total || payments.length}`, 14, 36);
  doc.text(`Total Revenue: ${formatCurrencyForExport(stats.total_revenue || 0)}`, 14, 42);
  
  // Prepare table data
  const tableData = payments.map(payment => [
    (payment.username || '').substring(0, 15),
    (payment.plan_name || '').substring(0, 12),
    formatCurrencyForExport(payment.amount / 100, payment.currency || 'INR'),
    payment.status || '',
    formatDateForExport(payment.created_at || payment.payment_date)
  ]);
  
  // Add table
  doc.autoTable({
    head: [['User', 'Plan', 'Amount', 'Status', 'Date']],
    body: tableData,
    startY: 50,
    theme: 'grid',
    headStyles: { fillColor: [212, 175, 55], textColor: [26, 26, 46] },
    styles: { fontSize: 8 },
    columnStyles: {
      0: { cellWidth: 35 },
      1: { cellWidth: 30 },
      2: { cellWidth: 30 },
      3: { cellWidth: 25 },
      4: { cellWidth: 40 }
    },
    alternateRowStyles: { fillColor: [245, 245, 245] }
  });
  
  // Add footer
  const pageCount = doc.internal.getNumberOfPages();
  doc.setFontSize(8);
  doc.setTextColor(128, 128, 128);
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.text(`Page ${i} of ${pageCount}`, doc.internal.pageSize.getWidth() - 30, doc.internal.pageSize.getHeight() - 10);
  }
  
  doc.save(filename);
};

