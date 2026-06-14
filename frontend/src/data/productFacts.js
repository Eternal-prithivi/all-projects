/**
 * Single source of truth for product copy (help, marketing, billing labels).
 * Mirrors backend PLANS in routes_payments.py — keep in sync when plans change.
 */

export const PATHS = {
  dashboard: '/dashboard',
  billing: '/dashboard/billing',
  pricing: '/dashboard/pricing',
  publicPricing: '/pricing',
  costs: '/dashboard/costs',
  team: '/dashboard/team',
  support: '/dashboard/support',
  contact: '/contact',
  profile: '/dashboard/profile',
  settings: '/dashboard/settings',
  securitySettings: '/dashboard/security-settings',
  vmCluster: '/dashboard/vmcluster',
  storage: '/dashboard/storage',
  security: '/dashboard/security',
  provision: '/dashboard/provision',
  download: '/download',
};

/** Features not yet shipped — referenced honestly in help copy */
export const NOT_YET_AVAILABLE = {
  vmMigration: 'VM migration between cloud providers is not available in the UI yet.',
  orgBilling:
    'When you join a team, your Zenith plan and seat are managed by the organization owner. Cloud provider costs remain on each member’s connected accounts.',
  apiKeysPage: 'API key management is planned; use dashboard features via the web UI today.',
};

/** Team page — what works today vs planned (honest UX) */
export const TEAM_CAPABILITIES = {
  today: [
    'Seat-based org billing (one subscription, multiple seats)',
    'Invite colleagues and manage roles',
    'Org-wide cloud spend and resource totals',
    'Shared resources with admin/member access rules',
    'Team budget alerts and provision approvals',
  ],
  comingSoon: ['Automatic seat proration via Razorpay subscriptions API'],
};

export const SUPPORT_EMAIL =
  import.meta.env.VITE_SUPPORT_EMAIL || 'support@zenithapp.io';

/** Plan catalog — aligned with backend PaymentPlan definitions */
export const PRODUCT_PLANS = [
  {
    plan_id: 'free',
    name: 'Free',
    tier: 'Free',
    description: 'Explore Zenith with demo dashboards and platform cloud',
    price_monthly: 0,
    price_yearly: 0,
    vm_limit: 2,
    storage_gb: 10,
    featured: false,
    cta: 'Get Started Free',
    ctaTo: '/register',
    features: [
      '2 VMs (Performance + Storage clusters)',
      '10 GB org storage quota',
      'Demo cost dashboard & cached VM metrics',
      'Storage uploads via platform cloud',
      'Provision templates — deploy with platform keys',
      'Community support (Help Center)',
    ],
  },
  {
    plan_id: 'basic',
    name: 'Basic',
    tier: 'Basic',
    description: 'Real multi-cloud ops for solo builders',
    price_monthly: 499,
    price_yearly: 4990,
    vm_limit: 5,
    storage_gb: 50,
    featured: false,
    cta: 'Get Started',
    ctaTo: '/register',
    features: [
      '5 VMs + active provisioned stacks',
      '50 GB org storage',
      'Live AWS · GCP · Azure (platform keys)',
      'Intelligent storage tiering',
      'Infrastructure Build wizard (Terraform + SDK)',
      'Cost & usage dashboard',
      'Email support (24h)',
    ],
  },
  {
    plan_id: 'pro',
    name: 'Pro',
    tier: 'Pro',
    description: 'Teams with BYOC, governance, and AI insights',
    price_monthly: 1499,
    price_yearly: 14990,
    vm_limit: 15,
    storage_gb: 200,
    featured: true,
    cta: 'Get Started',
    ctaTo: '/register',
    features: [
      '15 VMs + active provisioned stacks',
      '200 GB org storage',
      'BYOC — your AWS · GCP · Azure accounts',
      'Org billing with seat-based plans',
      'Provision policies, audit log & approvals',
      'AI storage & cost recommendations',
      'Priority support (4h)',
      'REST API access',
    ],
  },
  {
    plan_id: 'enterprise',
    name: 'Enterprise',
    tier: 'Enterprise',
    description: 'Org-wide governance, unlimited scale, dedicated onboarding',
    price_monthly: 4999,
    price_yearly: 49990,
    vm_limit: 999,
    storage_gb: 1000,
    featured: false,
    cta: 'Contact Sales',
    ctaTo: '/contact',
    features: [
      'Unlimited VMs & provisioned stacks',
      '1 TB org storage quota',
      'Everything in Pro + hybrid BYOC routing',
      'Org resource ACL, reassign & budget approvals',
      'Custom provision policies & audit export',
      'Team spend rollups & recommendations',
      'Dedicated onboarding — custom SLA on request',
    ],
  },
];

/** Compact capability blocks for pricing cards (dashboard) */
export function getPlanCapabilityBlocks(plan) {
  const vm =
    plan.vm_limit >= 999 ? 'Unlimited VMs' : `${plan.vm_limit} VMs + stacks`;
  const storage =
    plan.storage_gb >= 1000 ? '1 TB org storage' : `${plan.storage_gb} GB org storage`;

  const byPlan = {
    free: [
      { title: 'Compute', detail: vm },
      { title: 'Storage', detail: storage },
      { title: 'Provisioning', detail: 'Templates · platform keys' },
      { title: 'Insights', detail: 'Demo dashboard' },
    ],
    basic: [
      { title: 'Compute', detail: vm },
      { title: 'Storage', detail: storage },
      { title: 'Provisioning', detail: 'Build wizard · Terraform + SDK' },
      { title: 'Cloud', detail: 'AWS · GCP · Azure live' },
    ],
    pro: [
      { title: 'Compute', detail: vm },
      { title: 'BYOC & Teams', detail: 'Your clouds · seat billing' },
      { title: 'Provisioning', detail: 'Policies · audit · approvals' },
      { title: 'Intelligence', detail: 'AI recommendations · API' },
    ],
    enterprise: [
      { title: 'Scale', detail: vm },
      { title: 'Governance', detail: 'ACL · budgets · custom policies' },
      { title: 'Provisioning', detail: 'Full audit export · hybrid routing' },
      { title: 'Support', detail: 'Dedicated onboarding' },
    ],
  };

  return (
    byPlan[plan.plan_id] ?? [
      { title: 'Compute', detail: vm },
      { title: 'Storage', detail: storage },
      { title: 'Includes', detail: plan.features?.[0] ?? '—' },
      { title: 'Plus', detail: plan.features?.[1] ?? '—' },
    ]
  );
}

export function formatPlanPriceInr(amount) {
  if (!amount) return '₹0';
  return `₹${Number(amount).toLocaleString('en-IN')}`;
}

export function formatPlansSummaryForHelp() {
  return PRODUCT_PLANS.map((p) => {
    const vmLabel = p.vm_limit >= 999 ? 'Unlimited VMs' : `${p.vm_limit} VMs`;
    const storageLabel =
      p.storage_gb >= 1000 ? '1 TB org storage' : `${p.storage_gb} GB org storage`;
    const price =
      p.price_monthly === 0
        ? 'Free'
        : `${formatPlanPriceInr(p.price_monthly)}/month`;
    return `${p.name} (${price}, ${vmLabel}, ${storageLabel})`;
  }).join('; ');
}

/** Marketing grid for landing / public pricing */
export const MARKETING_PRICING = PRODUCT_PLANS.map((p) => ({
  tier: p.tier,
  description: p.description,
  amount:
    p.price_monthly === 0
      ? '0'
      : p.price_monthly.toLocaleString('en-IN'),
  featured: p.featured,
  features: p.features,
  cta: p.cta,
  ctaTo: p.ctaTo,
}));

export function buildHelpFaqs() {
  const plansSummary = formatPlansSummaryForHelp();
  const deleteAccountAnswer = `To delete your account, contact us via ${PATHS.contact} or email ${SUPPORT_EMAIL} with your username and reason for deletion. We process requests within 7 business days. Account deletion is permanent — export any data you need first.`;

  return [
    {
      id: 1,
      category: 'getting-started',
      question: 'How do I get started with Zenith?',
      answer: `Create an account from the homepage, then open your dashboard at ${PATHS.dashboard}. Choose a plan on ${PATHS.pricing} or stay on the free tier. You can create VMs, upload files, provision infrastructure, and run cost analysis from the sidebar.`,
    },
    {
      id: 2,
      category: 'getting-started',
      question: 'What cloud providers does Zenith support?',
      answer:
        'Zenith supports Amazon Web Services (AWS), Google Cloud Platform (GCP), and Microsoft Azure. Connect your clouds via BYOC on Pro and Enterprise plans, or use platform keys where configured on Free and Basic.',
    },
    {
      id: 3,
      category: 'getting-started',
      question: 'Is there a free plan?',
      answer: `Yes. The Free tier includes ${PRODUCT_PLANS[0].vm_limit} VMs, ${PRODUCT_PLANS[0].storage_gb} GB org storage, demo cost dashboards, provision templates with platform keys, and community support — no credit card required. Upgrade anytime from ${PATHS.billing}.`,
    },
    {
      id: 4,
      category: 'getting-started',
      question: 'What are the system requirements?',
      answer:
        'Use Zenith in any modern browser (Chrome, Firefox, Safari, Edge) or install the free desktop app for macOS, Windows, or Linux from /download. An internet connection is required. REST APIs are available on Pro and Enterprise for automation.',
    },
    {
      id: 5,
      category: 'billing',
      question: 'What subscription plans are available?',
      answer: `We offer: ${plansSummary}. Paid plans unlock live billing data, provisioning, and (on Pro+) BYOC and team governance. See ${PATHS.publicPricing} for the latest pricing.`,
    },
    {
      id: 28,
      category: 'billing',
      question: 'Why do I see a lock icon in the dashboard?',
      answer:
        'Zenith shows every destination in the sidebar, but Pro and Enterprise features (BYOC, provision policies, cost optimization, API keys, org seat billing) display a lock badge when your plan does not include them. Click a locked item to compare plans and upgrade from Billing or Pricing.',
    },
    {
      id: 6,
      category: 'billing',
      question: 'How does billing work?',
      answer: `Subscriptions are billed in INR via Razorpay. Cloud pass-through usage (AWS/GCP/Azure) is estimated in USD and converted for your bill. View usage, renewal date, and history on ${PATHS.billing}.`,
    },
    {
      id: 7,
      category: 'billing',
      question: 'Can I change my plan anytime?',
      answer: `Yes. Upgrade or change plans from ${PATHS.pricing} or ${PATHS.billing}. Paid upgrades take effect after successful payment through Razorpay.`,
    },
    {
      id: 8,
      category: 'billing',
      question: 'What payment methods do you accept?',
      answer:
        'We accept major credit and debit cards and UPI through Razorpay. All transactions are encrypted and PCI-DSS compliant.',
    },
    {
      id: 9,
      category: 'billing',
      question: 'How do I cancel my subscription?',
      answer: `Manage your subscription from ${PATHS.billing}. Contact support via ${PATHS.contact} or ${PATHS.support} if you need help canceling. ${NOT_YET_AVAILABLE.orgBilling}`,
    },
    {
      id: 10,
      category: 'vms',
      question: 'How do I create a virtual machine?',
      answer: `Open ${PATHS.vmCluster} and request a VM. Choose Performance or Storage cluster type, configure specs, and select a cloud provider. Provisioning typically completes in a few minutes.`,
    },
    {
      id: 11,
      category: 'vms',
      question: 'What VM types are available?',
      answer:
        'Performance VMs suit CPU-intensive workloads; Storage VMs suit data-heavy workloads. Active provisioned stacks count toward the same VM quota on your plan.',
    },
    {
      id: 12,
      category: 'vms',
      question: 'How do I connect to my VM?',
      answer:
        'After provisioning, SSH connection details appear in the VM details panel. Use any SSH client with the provided hostname, username, and key.',
    },
    {
      id: 13,
      category: 'vms',
      question: 'Can I stop and restart VMs?',
      answer: `Yes. Stop VMs from ${PATHS.vmCluster} when idle to reduce compute charges. Disk storage may still incur cost while stopped.`,
    },
    {
      id: 14,
      category: 'vms',
      question: 'How do I migrate VMs between cloud providers?',
      answer: NOT_YET_AVAILABLE.vmMigration,
    },
    {
      id: 15,
      category: 'storage',
      question: 'How do I upload files to cloud storage?',
      answer: `Go to ${PATHS.storage} and upload files. Zenith can recommend a provider based on file profile and your preferences.`,
    },
    {
      id: 16,
      category: 'storage',
      question: 'What is intelligent storage tiering?',
      answer:
        'ML-based tiering can suggest hot, cool, or archive tiers based on access patterns to reduce storage cost. Enable tiering features from the Storage page where available.',
    },
    {
      id: 17,
      category: 'storage',
      question: 'Is my data encrypted?',
      answer: `Data is protected in transit with TLS. For at-rest encryption of sensitive files, use the Security vault on ${PATHS.security}. See our Trust Center for details.`,
    },
    {
      id: 18,
      category: 'storage',
      question: 'What storage limits exist?',
      answer: `Storage limits follow your plan (org-wide quota): Free ${PRODUCT_PLANS[0].storage_gb} GB, Basic ${PRODUCT_PLANS[1].storage_gb} GB, Pro ${PRODUCT_PLANS[2].storage_gb} GB, Enterprise 1 TB. Check ${PATHS.billing} for your current limits.`,
    },
    {
      id: 19,
      category: 'security',
      question: 'How do I enable two-factor authentication (2FA)?',
      answer: `Open ${PATHS.securitySettings}, enable 2FA, scan the QR code with an authenticator app, and confirm with a 6-digit code.`,
    },
    {
      id: 20,
      category: 'security',
      question: 'What happens if I lose my 2FA device?',
      answer:
        'Use your backup codes from setup (one-time each). After signing in, disable and re-enable 2FA with a new device. Contact support if you have no backup codes.',
    },
    {
      id: 21,
      category: 'security',
      question: 'How do I manage active sessions?',
      answer: `View and revoke sessions from ${PATHS.securitySettings} where session management is enabled for your account.`,
    },
    {
      id: 22,
      category: 'security',
      question: 'Are API keys secure?',
      answer: NOT_YET_AVAILABLE.apiKeysPage,
    },
    {
      id: 23,
      category: 'account',
      question: 'How do I change my password?',
      answer: `Go to ${PATHS.securitySettings} and use Change Password. Use a strong unique password and enable 2FA.`,
    },
    {
      id: 24,
      category: 'account',
      question: 'Can I update my email address?',
      answer: `Edit your profile on ${PATHS.profile}. You may need to verify the new email address.`,
    },
    {
      id: 25,
      category: 'account',
      question: 'How do I delete my account?',
      answer: deleteAccountAnswer,
    },
    {
      id: 26,
      category: 'account',
      question: 'How do I view my activity history?',
      answer: `Recent security-related activity is available under ${PATHS.securitySettings}. Notifications history is on ${PATHS.dashboard}/notifications.`,
    },
    {
      id: 27,
      category: 'getting-started',
      question: 'What is Infrastructure Provisioning?',
      answer: `Open ${PATHS.provision} to deploy AWS, GCP, or Azure stacks from templates or a guided Build wizard. Free users can explore templates with platform keys; Basic and above get live Terraform and SDK engines. Pro and Enterprise add policy checks, audit logs, and org approval gates.`,
    },
  ];
}

/** Desktop download page FAQ */
export const DESKTOP_DOWNLOAD_FAQ = [
  {
    id: 'desktop-1',
    question: 'Does the desktop app work offline?',
    answer:
      'No. The desktop app is a native window around the same Zenith website. You need an internet connection to sign in and manage your clouds.',
  },
  {
    id: 'desktop-2',
    question: 'Why does my OS warn about an unknown publisher?',
    answer:
      'Beta builds are not code-signed yet. macOS Gatekeeper and Windows SmartScreen may show a warning. Follow the install steps on this page, or use Zenith in your browser with no install.',
  },
  {
    id: 'desktop-3',
    question: 'Is the desktop app different from the browser version?',
    answer:
      'No — it loads the same Zenith experience as Chrome or Edge. Updates ship when we deploy the website; reinstall only when we publish a new desktop shell version.',
  },
  {
    id: 'desktop-4',
    question: 'Where are releases hosted?',
    answer:
      'Installers are published on GitHub Releases when we push a desktop-v*.*.* tag. This page reads version metadata from releases.json.',
  },
];

export function getPlanById(planId) {
  return PRODUCT_PLANS.find((p) => p.plan_id === planId);
}
