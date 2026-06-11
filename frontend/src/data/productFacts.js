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
};

/** Features not yet shipped — referenced honestly in help copy */
export const NOT_YET_AVAILABLE = {
  vmMigration: 'VM migration between cloud providers is not available in the UI yet.',
  orgBilling: 'Organization billing is per Zenith account today; shared org billing is planned.',
  apiKeysPage: 'API key management is planned; use dashboard features via the web UI today.',
};

export const SUPPORT_EMAIL =
  import.meta.env.VITE_SUPPORT_EMAIL || 'support@zenithapp.io';

/** Plan catalog — aligned with backend PaymentPlan definitions */
export const PRODUCT_PLANS = [
  {
    plan_id: 'free',
    name: 'Free Tier',
    tier: 'Free',
    price_monthly: 0,
    price_yearly: 0,
    vm_limit: 2,
    storage_gb: 10,
    featured: false,
    cta: 'Get Started Free',
    ctaTo: '/register',
    features: [
      '2 VMs (demo mode)',
      '10 GB storage per VM',
      'Basic monitoring',
      'Community support',
    ],
  },
  {
    plan_id: 'basic',
    name: 'Basic',
    tier: 'Basic',
    price_monthly: 499,
    price_yearly: 4990,
    vm_limit: 5,
    storage_gb: 50,
    featured: false,
    cta: 'Get Started',
    ctaTo: '/register',
    features: [
      '5 VMs',
      '50 GB storage per VM',
      'Real-time monitoring',
      'Email support (24h)',
      'Real cloud resources (AWS, GCP, Azure)',
    ],
  },
  {
    plan_id: 'pro',
    name: 'Professional',
    tier: 'Professional',
    price_monthly: 1499,
    price_yearly: 14990,
    vm_limit: 15,
    storage_gb: 200,
    featured: true,
    cta: 'Get Started',
    ctaTo: '/register',
    features: [
      '15 VMs',
      '200 GB storage per VM',
      'AI recommendations',
      'Priority support (4h)',
      'Cost analytics',
      'API access',
    ],
  },
  {
    plan_id: 'enterprise',
    name: 'Enterprise',
    tier: 'Enterprise',
    price_monthly: 4999,
    price_yearly: 49990,
    vm_limit: 999,
    storage_gb: 1000,
    featured: false,
    cta: 'Contact Sales',
    ctaTo: '/contact',
    features: [
      'Unlimited VMs',
      '1 TB storage per VM',
      'Predictive analytics',
      '24/7 phone support',
      'Dedicated account manager',
      'SLA guarantee',
    ],
  },
];

export function formatPlanPriceInr(amount) {
  if (!amount) return '₹0';
  return `₹${Number(amount).toLocaleString('en-IN')}`;
}

export function formatPlansSummaryForHelp() {
  return PRODUCT_PLANS.map((p) => {
    const vmLabel = p.vm_limit >= 999 ? 'Unlimited VMs' : `${p.vm_limit} VMs`;
    const storageLabel =
      p.storage_gb >= 1000 ? '1 TB per VM' : `${p.storage_gb} GB per VM`;
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
      answer: `Create an account from the homepage, then open your dashboard at ${PATHS.dashboard}. Choose a plan on ${PATHS.pricing} or stay on the free tier. You can create VMs, upload files, and run cost analysis from the sidebar.`,
    },
    {
      id: 2,
      category: 'getting-started',
      question: 'What cloud providers does Zenith support?',
      answer:
        'Zenith supports Amazon Web Services (AWS), Google Cloud Platform (GCP), and Microsoft Azure. Connect your clouds via BYOC (bring your own credentials) or use platform keys where configured.',
    },
    {
      id: 3,
      category: 'getting-started',
      question: 'Is there a free plan?',
      answer: `Yes. The Free tier includes ${PRODUCT_PLANS[0].vm_limit} VMs, ${PRODUCT_PLANS[0].storage_gb} GB storage per VM, basic monitoring, and community support — no credit card required. Upgrade anytime from ${PATHS.billing}.`,
    },
    {
      id: 4,
      category: 'getting-started',
      question: 'What are the system requirements?',
      answer:
        'Zenith runs in any modern browser (Chrome, Firefox, Safari, Edge). No local install is required. REST APIs are available on paid plans for automation.',
    },
    {
      id: 5,
      category: 'billing',
      question: 'What subscription plans are available?',
      answer: `We offer: ${plansSummary}. All paid plans include multi-cloud management and cost tools. See ${PATHS.publicPricing} for the latest pricing.`,
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
        'Performance VMs suit CPU-intensive workloads; Storage VMs suit data-heavy workloads. Limits depend on your plan.',
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
      answer: `Storage limits follow your plan (per VM): Free ${PRODUCT_PLANS[0].storage_gb} GB, Basic ${PRODUCT_PLANS[1].storage_gb} GB, Professional ${PRODUCT_PLANS[2].storage_gb} GB, Enterprise 1 TB. Check ${PATHS.billing} for your current limits.`,
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
  ];
}

export function getPlanById(planId) {
  return PRODUCT_PLANS.find((p) => p.plan_id === planId);
}
