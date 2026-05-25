import React from 'react';

const iconProps = {
  stroke: 'currentColor',
  fill: 'none',
  strokeWidth: 2,
  viewBox: '0 0 24 24',
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  height: '1em',
  width: '1em',
  xmlns: 'http://www.w3.org/2000/svg',
};

export const IconDashboard = (props) => (
  <svg {...iconProps} {...props}><rect width="7" height="9" x="3" y="3" rx="1"></rect><rect width="7" height="5" x="14" y="3" rx="1"></rect><rect width="7" height="9" x="14" y="12" rx="1"></rect><rect width="7" height="5" x="3" y="16" rx="1"></rect></svg>
);

export const IconBarChart = (props) => (
  <svg {...iconProps} {...props}><line x1="12" x2="12" y1="20" y2="10"></line><line x1="18" x2="18" y1="20" y2="4"></line><line x1="6" x2="6" y1="20" y2="16"></line></svg>
);

export const IconHardDrive = (props) => (
  <svg {...iconProps} {...props}><line x1="22" x2="2" y1="12" y2="12"></line><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"></path><line x1="6" x2="6.01" y1="16" y2="16"></line><line x1="10" x2="10.01" y1="16" y2="16"></line></svg>
);

export const IconServer = (props) => (
  <svg {...iconProps} {...props}><rect width="20" height="8" x="2" y="2" rx="2" ry="2"></rect><rect width="20" height="8" x="2" y="14" rx="2" ry="2"></rect><line x1="6" x2="6.01" y1="6" y2="6"></line><line x1="6" x2="6.01" y1="18" y2="18"></line></svg>
);

export const IconShield = (props) => (
  <svg {...iconProps} {...props}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
);

// ... (keep all the existing icons above this line) ...

// --- Add these two new icons ---

export const IconDollarSign = (props) => (
  <svg {...iconProps} {...props}><circle cx="12" cy="12" r="10"></circle><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"></path><path d="M12 18V6"></path></svg>
);

export const IconShieldCheck = (props) => (
  <svg {...iconProps} {...props}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><path d="m9 12 2 2 4-4"></path></svg>
);
// ... (keep all existing icons)

// --- Add these new icons ---
export const IconDownload = (props) => (
  <svg {...iconProps} {...props}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" x2="12" y1="15" y2="3"></line></svg>
);

export const IconTrash = (props) => (
  <svg {...iconProps} {...props}><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
);
export const IconAlert = (props) => (
  <svg {...iconProps} {...props}><path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><path d="M12 9v4"></path><path d="M12 17h.01"></path></svg>
);

export const IconLock = (props) => (
  <svg {...iconProps} {...props}>
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
  </svg>
);

export const IconRefresh = (props) => (
  <svg {...iconProps} {...props}>
    <path d="M21 12a9 9 0 0 1-15.5 6.2"></path>
    <path d="M3 12A9 9 0 0 1 18.5 5.8"></path>
    <path d="M18 2v4h4"></path>
    <path d="M6 22v-4H2"></path>
  </svg>
);

export const IconUploadCloud = (props) => (
  <svg {...iconProps} {...props}>
    <path d="M16 16l-4-4-4 4"></path>
    <path d="M12 12v9"></path>
    <path d="M20.4 17.6A5 5 0 0 0 18 8h-1.3A8 8 0 1 0 4 16.3"></path>
  </svg>
);

export const IconSearch = (props) => (
  <svg {...iconProps} {...props}>
    <circle cx="11" cy="11" r="8"></circle>
    <path d="m21 21-4.3-4.3"></path>
  </svg>
);

export const IconActivity = (props) => (
  <svg {...iconProps} {...props}>
    <path d="M22 12h-4l-3 8L9 4l-3 8H2"></path>
  </svg>
);

export const IconZap = (props) => (
  <svg {...iconProps} {...props}>
    <path d="M13 2 3 14h8l-1 8 10-12h-8l1-8z"></path>
  </svg>
);

export const IconTarget = (props) => (
  <svg {...iconProps} {...props}>
    <circle cx="12" cy="12" r="10"></circle>
    <circle cx="12" cy="12" r="6"></circle>
    <circle cx="12" cy="12" r="2"></circle>
  </svg>
);

export const IconPlus = (props) => (
  <svg {...iconProps} {...props}>
    <path d="M12 5v14"></path>
    <path d="M5 12h14"></path>
  </svg>
);

export const IconArrowRightLeft = (props) => (
  <svg {...iconProps} {...props}>
    <path d="m16 3 4 4-4 4"></path>
    <path d="M20 7H4"></path>
    <path d="m8 21-4-4 4-4"></path>
    <path d="M4 17h16"></path>
  </svg>
);

export const IconClipboardList = (props) => (
  <svg {...iconProps} {...props}>
    <rect width="8" height="4" x="8" y="2" rx="1"></rect>
    <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
    <path d="M9 12h6"></path>
    <path d="M9 16h6"></path>
    <path d="M9 8h.01"></path>
  </svg>
);

export const IconChevronLeft = (props) => (
  <svg {...iconProps} {...props}>
    <path d="m15 18-6-6 6-6"></path>
  </svg>
);

export const IconClock = (props) => (
  <svg {...iconProps} {...props}>
    <circle cx="12" cy="12" r="10"></circle>
    <path d="M12 6v6l4 2"></path>
  </svg>
);

export const IconDatabase = (props) => (
  <svg {...iconProps} {...props}>
    <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
    <path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"></path>
    <path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"></path>
  </svg>
);

export const IconGlobe = (props) => (
  <svg {...iconProps} {...props}>
    <circle cx="12" cy="12" r="10"></circle>
    <path d="M2 12h20"></path>
    <path d="M12 2a15.3 15.3 0 0 1 0 20"></path>
    <path d="M12 2a15.3 15.3 0 0 0 0 20"></path>
  </svg>
);

export const IconPackage = (props) => (
  <svg {...iconProps} {...props}>
    <path d="m21 8-9-5-9 5 9 5 9-5Z"></path>
    <path d="M3 8v8l9 5 9-5V8"></path>
    <path d="M12 13v8"></path>
  </svg>
);

export const IconTag = (props) => (
  <svg {...iconProps} {...props}>
    <path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8Z"></path>
    <path d="M7.5 7.5h.01"></path>
  </svg>
);

export const IconLightbulb = (props) => (
  <svg {...iconProps} {...props}>
    <path d="M9 18h6"></path>
    <path d="M10 22h4"></path>
    <path d="M8.5 14.5A6 6 0 1 1 15.5 14.5c-.9.7-1.5 1.6-1.5 2.5h-4c0-.9-.6-1.8-1.5-2.5Z"></path>
  </svg>
);
