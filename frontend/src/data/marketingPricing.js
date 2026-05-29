/** Shared pricing tiers for landing and public /pricing page */
export const MARKETING_PRICING = [
  {
    tier: 'Free',
    amount: '0',
    featured: false,
    features: ['2 VMs (demo mode)', '10 GB storage', 'Basic monitoring', 'Community support'],
    cta: 'Get Started Free',
    ctaTo: '/register',
  },
  {
    tier: 'Basic',
    amount: '499',
    featured: false,
    features: ['5 VMs', '50 GB storage', 'Real-time monitoring', 'Email support', 'Real cloud resources'],
    cta: 'Get Started',
    ctaTo: '/register',
  },
  {
    tier: 'Professional',
    amount: '1,499',
    featured: true,
    features: [
      '15 VMs',
      '200 GB storage',
      'AI recommendations',
      'Priority support',
      'Cost analytics',
      'API access',
    ],
    cta: 'Get Started',
    ctaTo: '/register',
  },
  {
    tier: 'Enterprise',
    amount: '4,999',
    featured: false,
    features: [
      'Unlimited VMs',
      '1 TB storage',
      'Predictive analytics',
      '24/7 phone support',
      'Dedicated manager',
      'SLA guarantee',
    ],
    cta: 'Contact Sales',
    ctaTo: '/contact',
  },
];
