// ProvisionDeployWizard.jsx — intent-first stack provisioning (uses BYOC from Settings)
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { FaDatabase, FaGlobe, FaServer } from 'react-icons/fa';
import api from '../../api';
import { getApiBaseUrl, getApiRoot } from '../../config/apiBase.js';
import ProvisionIntentPanel from './ProvisionIntentPanel.jsx';
import TriCloudComparePanel from './TriCloudComparePanel.jsx';
import PlainEnglishReview from './PlainEnglishReview.jsx';
import ProvisionSuccessPanel from './ProvisionSuccessPanel.jsx';

/** API catalog uses icon keys; map to react-icons for consistent 48×48 tiles. */
const TEMPLATE_ICON_MAP = {
  globe: FaGlobe,
  server: FaServer,
  database: FaDatabase,
};

function TemplateCardIcon({ icon }) {
  const Icon = TEMPLATE_ICON_MAP[icon];
  if (Icon) {
    return <Icon className="template-card-icon-svg" aria-hidden />;
  }
  if (icon && typeof icon === 'string' && icon.length <= 4) {
    return <span className="template-card-icon-emoji">{icon}</span>;
  }
  return <FaGlobe className="template-card-icon-svg" aria-hidden />;
}

const TEMPLATES = [
  {
    key: 'static-site',
    name: 'Static Website',
    description: 'Host a static HTML/CSS/JS website on S3. Private, encrypted, free tier eligible.',
    icon: 'globe',
    cost: '$0.00/month',
    services: { enable_s3: true },
  },
  {
    key: 'backend-app',
    name: 'Backend Application',
    description: 'EC2 instance with VPC networking, IAM role, and CloudWatch monitoring.',
    icon: 'server',
    cost: '$0.00/month',
    services: { enable_vpc: true, enable_ec2: true, enable_iam: true, enable_cloudwatch: true },
  },
  {
    key: 'serverless-db',
    name: 'Serverless Database',
    description: 'DynamoDB table with provisioned capacity within AWS always-free limits.',
    icon: 'database',
    cost: '$0.00/month',
    services: { enable_dynamodb: true },
  },
];

const MODULES = [
  { key: 'vpc', name: 'VPC', desc: 'Virtual Private Cloud with public/private subnets', flag: 'enable_vpc' },
  { key: 'ec2', name: 'EC2', desc: 'Elastic Compute Cloud instance', flag: 'enable_ec2', requires: ['vpc'] },
  { key: 's3', name: 'S3', desc: 'Simple Storage Service bucket', flag: 'enable_s3' },
  { key: 'iam', name: 'IAM', desc: 'Identity & Access Management role', flag: 'enable_iam' },
  { key: 'cloudwatch', name: 'CloudWatch', desc: 'Monitoring & alerting', flag: 'enable_cloudwatch', requires: ['ec2'] },
  { key: 'dynamodb', name: 'DynamoDB', desc: 'NoSQL database table', flag: 'enable_dynamodb' },
];

const STEP_LABELS = ['Intent', 'Cloud', 'Configure', 'Review', 'Build'];

/** Initial POST returns quickly; poll status for terraform output. */
const PLAN_START_TIMEOUT_MS = 120 * 1000;
const PLAN_POLL_INTERVAL_MS = 3000;
const PLAN_POLL_MAX_ATTEMPTS = 260;  // ~13 min — outlasts 480s plan timeout + init on Render
// Render free tier can be slow to answer while terraform init runs (512MB RAM).
const PLAN_POLL_REQUEST_TIMEOUT_MS = 120 * 1000;
const WAKE_MAX_WAIT_MS = 90 * 1000;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function isNetworkFailure(err) {
  return err?.message === 'Network Error' || err?.code === 'ERR_NETWORK';
}

function formatProvisionError(err, fallback, { duringPoll = false } = {}) {
  const data = err.response?.data;
  if (data && typeof data === 'object') {
    if (data.error) return String(data.error);
    if (data.detail) {
      if (typeof data.detail === 'string') return data.detail;
      if (Array.isArray(data.detail)) {
        return data.detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
      }
    }
    if (data.message) return String(data.message);
  }
  if (err.code === 'ECONNABORTED') {
    return 'Request timed out. Terraform may still be running — wait a minute, check Render logs, or try again.';
  }
  if (isNetworkFailure(err)) {
    if (duringPoll) {
      return (
        'Lost connection to the server while Terraform was running. ' +
        'On Render free tier the API often restarts during terraform plan. ' +
        'Open Render → confirm zenith-backend is Live, visit /health, then start a new plan ' +
        '(or check Deployments for a finished plan).'
      );
    }
    return (
      `Cannot reach the API at ${getApiBaseUrl()}. ` +
      'Open https://zenith-backend-707i.onrender.com/health in a tab and wait for {"status":"ok"}. ' +
      'Vercel: VITE_API_URL=https://zenith-backend-707i.onrender.com (no /api), then redeploy frontend.'
    );
  }
  if (err.response?.status) {
    return `${fallback} (HTTP ${err.response.status})`;
  }
  if (err.message) return err.message;
  return fallback;
}

/** Wait until Render health responds (free tier cold start / restart). */
async function waitForBackend(maxWaitMs = WAKE_MAX_WAIT_MS) {
  const deadline = Date.now() + maxWaitMs;
  let attempt = 0;
  while (Date.now() < deadline) {
    attempt += 1;
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 15000);
      const res = await fetch(`${getApiRoot()}/health`, {
        method: 'GET',
        cache: 'no-store',
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (res.ok) {
        return { ok: true, attempts: attempt };
      }
    } catch {
      // Render still waking or restarting
    }
    await sleep(Math.min(2500 + attempt * 200, 5000));
  }
  return { ok: false, attempts: attempt };
}

const CSP_OPTIONS = [
  { value: 'AWS', label: 'AWS' },
  { value: 'GCP', label: 'GCP' },
  { value: 'Azure', label: 'Azure' },
];

const EMPTY_FLAGS = {
  enable_vpc: false,
  enable_ec2: false,
  enable_s3: false,
  enable_iam: false,
  enable_cloudwatch: false,
  enable_dynamodb: false,
  enable_gcs: false,
  enable_gcp_network: false,
  enable_gce: false,
  enable_gcp_service_account: false,
  enable_gcp_monitoring: false,
  enable_firestore: false,
  enable_azure_storage: false,
  enable_vnet: false,
  enable_azure_vm: false,
  enable_azure_monitor: false,
  enable_cosmos: false,
  enable_billing: false,
};

export default function ProvisionDeployWizard({
  terraformOk: _terraformOk,
  userProvisionEngine = 'boto3',
  availableProviders = ['AWS', 'GCP', 'Azure'],
  defaultProvider = 'AWS',
  onDeployed,
}) {
  const [csp, setCsp] = useState(
    availableProviders.includes(defaultProvider) ? defaultProvider : availableProviders[0] || 'AWS'
  );
  const engineLabel =
    csp === 'AWS'
      ? userProvisionEngine === 'terraform'
        ? 'Terraform'
        : 'Boto3'
      : userProvisionEngine === 'terraform'
        ? 'Terraform'
        : 'Cloud SDK';
  const [templates, setTemplates] = useState(TEMPLATES);
  const [modules, setModules] = useState(MODULES);
  const [step, setStep] = useState(0);
  const [selectedTemplate, setSelectedTemplate] = useState(null);

  const [config, setConfig] = useState({
    csp: 'AWS',
    template: null,
    aws_region: 'ap-south-1',
    gcp_region: 'us-central1',
    gcp_project: '',
    azure_location: 'eastus',
    resource_group_name: 'zenith-rg',
    storage_account_name: '',
    container_name: 'zenith-static',
    enable_gcs: false,
    enable_gcp_network: false,
    enable_gce: false,
    enable_gcp_service_account: false,
    enable_gcp_monitoring: false,
    enable_firestore: false,
    machine_type: 'e2-micro',
    service_account_id: 'zenith-app-sa',
    firestore_database_id: '(default)',
    enable_azure_storage: false,
    enable_vnet: false,
    enable_azure_vm: false,
    enable_azure_monitor: false,
    enable_cosmos: false,
    vm_size: 'Standard_B1s',
    cosmos_account_name: '',
    cosmos_database_name: 'zenith-db',
    enable_vpc: false,
    enable_ec2: false,
    enable_s3: false,
    enable_iam: false,
    enable_cloudwatch: false,
    enable_dynamodb: false,
    enable_billing: false,
    vpc_cidr: '10.0.0.0/16',
    instance_type: 't2.micro',
    instance_name: '',
    ami_id: '',
    bucket_name: '',
    role_name: 'app-role',
    alarm_email: '',
    budget_limit: '1',
    budget_email: '',
    dynamodb_table_name: '',
    dynamodb_hash_key: 'id',
    dynamodb_read_capacity: 5,
    dynamodb_write_capacity: 5,
    tags: { Env: 'free-tier' },
    environment: 'free-tier',
    workload_description: '',
    size_profile: 'micro',
    disk_size_gb: 30,
    deployment_display_name: '',
  });

  const [workloadDescription, setWorkloadDescription] = useState('');
  const [followUpAnswers, setFollowUpAnswers] = useState({});
  const [intentAnalysis, setIntentAnalysis] = useState(null);
  const [isAnalyzingIntent, setIsAnalyzingIntent] = useState(false);
  const [cloudComparisons, setCloudComparisons] = useState([]);
  const [compareLoading, setCompareLoading] = useState(false);
  const [reviewSummary, setReviewSummary] = useState(null);
  const [reviewSummaryLoading, setReviewSummaryLoading] = useState(false);
  const [showAdvancedModules, setShowAdvancedModules] = useState(false);
  const [successOpen, setSuccessOpen] = useState(false);
  const [handoffData, setHandoffData] = useState(null);
  const intentDebounceRef = useRef(null);

  const [policyResult, setPolicyResult] = useState(null);
  const [costEstimate, setCostEstimate] = useState(null);
  const [planOutput, setPlanOutput] = useState('');
  const [deploymentId, setDeploymentId] = useState(null);
  const [planReady, setPlanReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const terminalRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [tRes, mRes] = await Promise.all([
          api.get('/provision/templates', { params: { csp } }),
          api.get('/provision/modules', { params: { csp } }),
        ]);
        if (!cancelled) {
          setTemplates(tRes.data.templates || []);
          setModules(mRes.data.modules || []);
        }
      } catch {
        if (!cancelled) {
          setTemplates([]);
          setModules([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [csp]);

  useEffect(() => {
    if (!availableProviders.includes(csp) && availableProviders.length > 0) {
      setCsp(availableProviders[0]);
      setConfig((prev) => ({ ...prev, csp: availableProviders[0] }));
    }
  }, [availableProviders, csp]);

  const handleCspChange = (next) => {
    setCsp(next);
    setSelectedTemplate(null);
    setStep(0);
    setConfig((prev) => ({ ...prev, csp: next, template: null, ...EMPTY_FLAGS }));
  };

  // ── Step 1: Template Selection ──
  const selectTemplate = (tmpl) => {
    if (selectedTemplate === tmpl.key) {
      // Deselect
      setSelectedTemplate(null);
      setConfig(prev => ({
        ...prev,
        template: null,
        ...EMPTY_FLAGS,
      }));
    } else {
      setSelectedTemplate(tmpl.key);
      const services = { ...EMPTY_FLAGS };
      Object.entries(tmpl.services || {}).forEach(([k, v]) => {
        services[k] = !!v;
      });
      setConfig(prev => ({
        ...prev,
        template: tmpl.key,
        ...services,
      }));
    }
  };

  const toggleModule = (flag) => {
    setSelectedTemplate(null); // Custom mode
    setConfig(prev => {
      const next = { ...prev, template: 'custom', [flag]: !prev[flag] };
      // Auto-enable VPC when EC2 is enabled
      if (flag === 'enable_ec2' && next.enable_ec2) next.enable_vpc = true;
      // Auto-enable EC2 when CloudWatch is enabled
      if (flag === 'enable_cloudwatch' && next.enable_cloudwatch) {
        next.enable_ec2 = true;
        next.enable_vpc = true;
      }
      if (flag === 'enable_gce' && next.enable_gce) next.enable_gcp_network = true;
      if (flag === 'enable_gcp_monitoring' && next.enable_gcp_monitoring) {
        next.enable_gce = true;
        next.enable_gcp_network = true;
      }
      if (flag === 'enable_azure_vm' && next.enable_azure_vm) next.enable_vnet = true;
      return next;
    });
  };

  const hasAnyModule = modules.some((m) => config[m.flag]);

  const applyTemplateByKey = useCallback(async (tmplKey, sizeProfile, trimmedDesc) => {
    let list = templates;
    if (!list.find((t) => t.key === tmplKey)) {
      try {
        const tRes = await api.get('/provision/templates', { params: { csp } });
        list = tRes.data.templates || [];
        setTemplates(list);
      } catch {
        list = [];
      }
    }
    const tmpl = list.find((t) => t.key === tmplKey);
    if (tmpl) {
      setSelectedTemplate(tmpl.key);
      const services = { ...EMPTY_FLAGS };
      Object.entries(tmpl.services || {}).forEach(([k, v]) => {
        services[k] = !!v;
      });
      setConfig((prev) => ({
        ...prev,
        template: tmpl.key,
        ...services,
        size_profile: sizeProfile || prev.size_profile || 'micro',
        workload_description: trimmedDesc ?? prev.workload_description,
      }));
    } else {
      setSelectedTemplate(tmplKey);
      setConfig((prev) => ({
        ...prev,
        template: tmplKey,
        size_profile: sizeProfile || 'micro',
        workload_description: trimmedDesc ?? prev.workload_description,
      }));
    }
  }, [templates, csp]);

  const runIntentAnalysis = useCallback(async () => {
    const trimmed = workloadDescription.trim();
    if (trimmed.length < 3) {
      setIntentAnalysis(null);
      return;
    }
    setIsAnalyzingIntent(true);
    try {
      const res = await api.post('/provision/analyze-intent', {
        workload_description: trimmed,
        follow_up_answers: Object.keys(followUpAnswers).length ? followUpAnswers : null,
      });
      setIntentAnalysis(res.data);
      if (res.data?.recommendation?.template) {
        await applyTemplateByKey(
          res.data.recommendation.template,
          res.data.recommendation.size_profile || 'micro',
          trimmed,
        );
      }
    } catch (err) {
      console.error('Intent analysis failed', err);
    } finally {
      setIsAnalyzingIntent(false);
    }
  }, [workloadDescription, followUpAnswers, applyTemplateByKey]);

  useEffect(() => {
    if (intentDebounceRef.current) clearTimeout(intentDebounceRef.current);
    if (workloadDescription.trim().length < 3) {
      setIntentAnalysis(null);
      return undefined;
    }
    intentDebounceRef.current = setTimeout(runIntentAnalysis, 500);
    return () => {
      if (intentDebounceRef.current) clearTimeout(intentDebounceRef.current);
    };
  }, [workloadDescription, followUpAnswers, runIntentAnalysis]);

  const loadCloudCompare = useCallback(async () => {
    const template = selectedTemplate || intentAnalysis?.recommendation?.template || 'backend-app';
    const sizeProfile = config.size_profile || intentAnalysis?.recommendation?.size_profile || 'micro';
    setCompareLoading(true);
    try {
      const res = await api.post('/provision/compare-clouds', {
        template,
        size_profile: sizeProfile,
        environment: config.environment,
        fit_base: intentAnalysis?.recommendation?.confidence || 70,
        reasons: intentAnalysis?.recommendation?.reasons,
      });
      setCloudComparisons(res.data.comparisons || []);
    } catch (err) {
      console.error('Cloud compare failed', err);
      setCloudComparisons([]);
    } finally {
      setCompareLoading(false);
    }
  }, [selectedTemplate, intentAnalysis, config.size_profile, config.environment]);

  useEffect(() => {
    if (step === 1) {
      loadCloudCompare();
    }
  }, [step, loadCloudCompare]);

  const applyCompareSelection = async (row) => {
    setCsp(row.csp);
    const tmplKey = row.template || selectedTemplate;
    try {
      const tRes = await api.get('/provision/templates', { params: { csp: row.csp } });
      const list = tRes.data.templates || [];
      setTemplates(list);
      const tmpl = list.find((t) => t.key === tmplKey);
      if (tmpl) selectTemplate(tmpl);
      else {
        setSelectedTemplate(tmplKey);
        setConfig((prev) => ({ ...prev, csp: row.csp, template: tmplKey }));
      }
    } catch {
      setConfig((prev) => ({
        ...prev,
        csp: row.csp,
        template: tmplKey,
        size_profile: prev.size_profile || 'micro',
      }));
    }
  };

  const handleFollowUpChange = (questionId, value) => {
    setFollowUpAnswers((prev) => {
      const next = { ...prev };
      if (!value) delete next[questionId];
      else next[questionId] = value;
      return next;
    });
  };

  // ── Config field update ──
  const updateConfig = (key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  // ── Step 4: Run plan ──
  const runPlan = async () => {
    setLoading(true);
    setError(null);
    setPlanOutput('');
    setPlanReady(false);
    const planStartedAt = Date.now();
    try {
      setPlanOutput('Waking Render API (first load can take up to 90s)…\n');
      const wake = await waitForBackend(WAKE_MAX_WAIT_MS);
      if (!wake.ok) {
        setError(
          'Render API did not respond in time. Open https://zenith-backend-707i.onrender.com/health ' +
          'in your browser, wait for {"status":"ok"}, then try again.'
        );
        return;
      }
      const res = await api.post('/provision/plan', config, {
        timeout: PLAN_START_TIMEOUT_MS,
      });
      setPolicyResult(res.data.policy_check);
      setCostEstimate(res.data.cost_estimate);
      setDeploymentId(res.data.deployment_id);
      const planEngine = res.data.provision_engine || userProvisionEngine;

      // Background plan — poll until done (avoids Render 502 on long terraform)
      if (res.data.status === 'running' && res.data.deployment_id) {
        setPlanOutput(`Starting ${planEngine === 'terraform' ? 'Terraform' : 'Boto3'} plan on the server…\n`);
        for (let attempt = 0; attempt < PLAN_POLL_MAX_ATTEMPTS; attempt += 1) {
          await sleep(PLAN_POLL_INTERVAL_MS);
          let st;
          try {
            st = await api.get(`/provision/plan/status/${res.data.deployment_id}`, {
              timeout: PLAN_POLL_REQUEST_TIMEOUT_MS,
            });
          } catch (pollErr) {
            // Timeout or network blip while server is busy with terraform — keep polling
            const retryable =
              isNetworkFailure(pollErr) || pollErr?.code === 'ECONNABORTED';
            if (retryable) {
              const reason =
                pollErr?.code === 'ECONNABORTED'
                  ? 'Server is busy (terraform init/plan) or Render restarted'
                  : 'API unreachable';
              setPlanOutput(
                `${reason}. Still working… poll ${attempt + 1}/${PLAN_POLL_MAX_ATTEMPTS}. ` +
                `Deployment: ${res.data.deployment_id}\n`
              );
              await waitForBackend(120 * 1000);
              continue;
            }
            throw pollErr;
          }
          const elapsedSec = Math.round((Date.now() - planStartedAt) / 1000);
          if (st.data.plan_output) {
            setPlanOutput(st.data.plan_output);
          } else if (!st.data.done) {
            const stage = st.data.stage || st.data.status || 'working';
            setPlanOutput(
              `${planEngine === 'terraform' ? 'Terraform' : 'Plan'} ${stage} in progress (${elapsedSec}s elapsed, poll ${attempt + 1}/${PLAN_POLL_MAX_ATTEMPTS})…\n`
            );
          }
          if (st.data.done) {
            if (!st.data.success) {
              const stage = st.data.stage ? `${st.data.stage}: ` : '';
              setError(stage + (st.data.error || st.data.plan_output || `${engineLabel} plan failed`));
            } else {
              setPlanReady(true);
            }
            return;
          }
        }
        setError(
          'Plan did not finish within ~13 minutes. ' +
          'Check Render logs for errors, or start a new plan (try enabling fewer modules).'
        );
        return;
      }

      // Immediate result: either fast path (boto3) success/failure, or legacy fast failure.
      setPlanOutput(res.data.plan_output || '');
      if (res.data.success) {
        setPlanReady(true);
      } else {
        const stage = res.data.stage ? `${res.data.stage}: ` : '';
        const detail = res.data.error || res.data.plan_output || 'Plan failed';
        setError(stage + detail);
      }
    } catch (err) {
      setError(formatProvisionError(err, `Failed to run ${engineLabel} plan`, {
        duringPoll: Boolean(deploymentId),
      }));
    } finally {
      setLoading(false);
    }
  };

  // ── Apply ──
  const runApply = async () => {
    if (!deploymentId || !planReady) return;
    setLoading(true);
    setError(null);
    setPlanOutput((prev) => `${prev}\n\nApplying changes in AWS (this can take several minutes)…\n`);
    try {
      const res = await api.post(`/provision/apply/${deploymentId}`, {
        timeout: 10 * 60 * 1000,
      });
      if (res.data.success) {
        setPlanOutput(prev => prev + '\n\n✅ Apply complete! ' + res.data.resources_count + ' resources created.');
        const depId = res.data.deployment_id || deploymentId;
        try {
          const handoffRes = await api.get(`/provision/deployments/${depId}/handoff`);
          setHandoffData(handoffRes.data);
        } catch {
          setHandoffData({
            deployment_id: depId,
            created_resources: res.data.created_resources || [],
            csp: config.csp,
          });
        }
        setSuccessOpen(true);
      } else {
        setError(res.data.error || `${engineLabel} apply failed`);
        setPlanOutput(prev => prev + '\n\n❌ Apply failed: ' + (res.data.error || 'unknown error'));
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to apply');
    } finally {
      setLoading(false);
    }
  };

  const nextStep = () => {
    if (step === 0 && workloadDescription.trim().length < 3) {
      setError('Please describe what you want to build.');
      return;
    }
    if (step === 0) {
      setConfig((prev) => ({
        ...prev,
        workload_description: workloadDescription.trim(),
        intent_recommendation: intentAnalysis?.recommendation,
      }));
    }
    if (step === 3) {
      if (!policyResult?.can_deploy) return;
      setStep(4);
      runPlan();
      return;
    }
    setStep((s) => Math.min(s + 1, 4));
  };

  const prevStep = () => {
    if (step === 3) {
      setPolicyResult(null);
      setCostEstimate(null);
      setReviewSummary(null);
    }
    setStep((s) => Math.max(s - 1, 0));
  };

  const downloadTerraformExport = async () => {
    if (!deploymentId) return;
    try {
      const res = await api.get(`/provision/deployments/${deploymentId}/export/terraform`, {
        responseType: 'blob',
      });
      const isZip = res.headers['content-type']?.includes('zip');
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = isZip ? `${deploymentId}-terraform.zip` : `${deploymentId}.tfvars.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.response?.data?.detail || 'Terraform export not available for this deployment');
    }
  };

  // Auto-run review when user reaches the Review step
  useEffect(() => {
    if (step !== 3) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setReviewSummaryLoading(true);
      setError(null);
      const payload = { ...config, csp, workload_description: workloadDescription.trim() };
      try {
        const [policyRes, costRes, summaryRes] = await Promise.all([
          api.post('/provision/policy-check', payload),
          api.post('/provision/estimate', payload),
          api.post('/provision/review-summary', payload),
        ]);
        if (cancelled) return;
        setPolicyResult(policyRes.data);
        setCostEstimate(costRes.data);
        setReviewSummary(summaryRes.data);
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || 'Failed to run review');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          setReviewSummaryLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once per visit to Review
  }, [step]);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [planOutput]);

  const canProceedStep0 = workloadDescription.trim().length >= 3;
  const canProceedStep1 = hasAnyModule && Boolean(csp);

  return (
    <div className="provision-deploy-wizard">
      <ProvisionSuccessPanel
        open={successOpen}
        handoff={handoffData}
        deploymentId={deploymentId}
        onClose={() => {
          setSuccessOpen(false);
          onDeployed?.();
        }}
        onViewDeployments={() => {
          setSuccessOpen(false);
          onDeployed?.();
        }}
      />

      <div className="section-header">
        <h3>Build a new stack</h3>
        <p>
          Describe what you need — we help you choose and build once. Provider: <strong>{csp}</strong> · Engine:{' '}
          <strong>{engineLabel}</strong>
          {csp === 'AWS' && ' (change in Settings → Infrastructure provisioning)'}.
        </p>
      </div>

      <div className="wizard-steps">
        {STEP_LABELS.map((label, i) => (
          <React.Fragment key={label}>
            <div className={`wizard-step ${i === step ? 'active' : i < step ? 'completed' : 'inactive'}`} onClick={() => i < step && setStep(i)}>
              <div className="wizard-step-number">{i < step ? '✓' : i + 1}</div>
              <span className="wizard-step-label">{label}</span>
            </div>
            {i < STEP_LABELS.length - 1 && <div className={`wizard-step-connector ${i < step ? 'completed' : ''}`} />}
          </React.Fragment>
        ))}
      </div>
      {error && (
        <div className="policy-item block" style={{ marginBottom: '1.5rem' }}>
          <div className="policy-item-name">⚠️ Error</div>
          <div className="policy-item-desc">{error}</div>
        </div>
      )}

      {/* Step 0: Intent */}
      {step === 0 && (
        <div>
          <ProvisionIntentPanel
            workloadDescription={workloadDescription}
            onWorkloadChange={setWorkloadDescription}
            analysis={intentAnalysis}
            isAnalyzing={isAnalyzingIntent}
            followUpAnswers={followUpAnswers}
            onFollowUpChange={handleFollowUpChange}
          />
          <div className="provision-actions">
            <button className="btn-provision primary" disabled={!canProceedStep0} onClick={nextStep} type="button">
              Next: Compare clouds →
            </button>
          </div>
        </div>
      )}

      {/* Step 1: Cloud & template */}
      {step === 1 && (
        <div>
          <TriCloudComparePanel
            comparisons={cloudComparisons}
            loading={compareLoading}
            selectedCsp={csp}
            onSelect={applyCompareSelection}
            templates={templates}
            selectedTemplate={selectedTemplate}
            onSelectTemplate={(tmpl) => selectTemplate(tmpl)}
          />
          <button
            type="button"
            className="btn-provision secondary"
            style={{ marginTop: '1rem' }}
            onClick={() => setShowAdvancedModules((v) => !v)}
          >
            {showAdvancedModules ? 'Hide advanced modules' : 'Advanced: customize modules'}
          </button>
          {showAdvancedModules && (
            <div className="module-toggles" style={{ marginTop: '1rem' }}>
              {modules.map(mod => (
                <div
                  key={mod.key}
                  className={`module-toggle ${config[mod.flag] ? 'enabled' : ''}`}
                  onClick={() => toggleModule(mod.flag)}
                  id={`module-${mod.key}`}
                >
                  <div className="module-toggle-switch" />
                  <div className="module-toggle-info">
                    <h4>{mod.name}</h4>
                    <p>{mod.desc || mod.name}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="provision-actions">
            <button className="btn-provision secondary" onClick={prevStep} type="button">← Back</button>
            <button className="btn-provision primary" disabled={!canProceedStep1} onClick={nextStep} type="button">
              Next: Configure →
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Configure */}
      {step === 2 && (
        <div>
          <div className="section-header">
            <h3>Configure Resources</h3>
            <p>Set parameters for your selected modules. Defaults are free-tier safe.</p>
          </div>

          <div className="config-form">
            <div className="config-field">
              <label htmlFor="provision-display-name">Deployment name</label>
              <input
                id="provision-display-name"
                type="text"
                value={config.deployment_display_name}
                onChange={(e) => updateConfig('deployment_display_name', e.target.value)}
                placeholder="my-api-stack"
              />
            </div>
            <div className="config-field">
              <label htmlFor="provision-environment">Environment</label>
              <select
                id="provision-environment"
                className="zenith-select"
                value={config.environment}
                onChange={(e) => updateConfig('environment', e.target.value)}
              >
                <option value="dev">Development</option>
                <option value="staging">Staging</option>
                <option value="prod">Production</option>
                <option value="free-tier">Free tier / learning</option>
              </select>
            </div>
            {(config.enable_ec2 || config.enable_gce || config.enable_azure_vm) && (
              <div className="config-field">
                <label htmlFor="provision-disk-gb">Boot disk size (GB)</label>
                <input
                  id="provision-disk-gb"
                  type="number"
                  min={8}
                  max={2000}
                  value={config.disk_size_gb}
                  onChange={(e) => updateConfig('disk_size_gb', Number(e.target.value))}
                />
              </div>
            )}
            {csp === 'AWS' && (
            <div className="config-field">
              <label>AWS Region</label>
              <select className="zenith-select" value={config.aws_region} onChange={e => updateConfig('aws_region', e.target.value)}>
                <option value="ap-south-1">Asia Pacific (Mumbai)</option>
                <option value="us-east-1">US East (N. Virginia)</option>
                <option value="us-west-2">US West (Oregon)</option>
                <option value="eu-west-1">Europe (Ireland)</option>
                <option value="ap-southeast-1">Asia Pacific (Singapore)</option>
              </select>
            </div>
            )}

            {csp === 'GCP' && (
              <>
                <div className="config-field">
                  <label>GCP Region</label>
                  <select className="zenith-select" value={config.gcp_region} onChange={e => updateConfig('gcp_region', e.target.value)}>
                    <option value="us-central1">us-central1</option>
                    <option value="us-east1">us-east1</option>
                    <option value="europe-west1">europe-west1</option>
                  </select>
                </div>
                {config.enable_gcs && (
                  <div className="config-field">
                    <label>GCS Bucket Name (globally unique)</label>
                    <input
                      type="text"
                      value={config.bucket_name}
                      onChange={e => updateConfig('bucket_name', e.target.value)}
                      placeholder="my-zenith-static-site"
                    />
                  </div>
                )}
                {config.enable_gce && (
                  <>
                    <div className="config-field">
                      <label>Machine Type</label>
                      <select className="zenith-select" value={config.machine_type} onChange={e => updateConfig('machine_type', e.target.value)}>
                        <option value="e2-micro">e2-micro (Free tier eligible)</option>
                        <option value="e2-small">e2-small</option>
                        <option value="e2-medium">e2-medium</option>
                      </select>
                    </div>
                    <div className="config-field">
                      <label>VM Name</label>
                      <input
                        type="text"
                        value={config.instance_name}
                        onChange={e => updateConfig('instance_name', e.target.value)}
                        placeholder="zenith-gce-app"
                      />
                    </div>
                  </>
                )}
                {config.enable_gcp_service_account && (
                  <div className="config-field">
                    <label>Service Account ID</label>
                    <input
                      type="text"
                      value={config.service_account_id}
                      onChange={e => updateConfig('service_account_id', e.target.value)}
                      placeholder="zenith-app-sa"
                    />
                  </div>
                )}
                {config.enable_gcp_monitoring && (
                  <div className="config-field">
                    <label>Alert Email</label>
                    <input
                      type="email"
                      value={config.alarm_email}
                      onChange={e => updateConfig('alarm_email', e.target.value)}
                      placeholder="admin@example.com"
                    />
                  </div>
                )}
                {config.enable_firestore && (
                  <div className="config-field">
                    <label>Firestore Database ID</label>
                    <input
                      type="text"
                      value={config.firestore_database_id}
                      onChange={e => updateConfig('firestore_database_id', e.target.value)}
                      placeholder="(default)"
                    />
                  </div>
                )}
              </>
            )}

            {csp === 'Azure' && (
              <>
                <div className="config-field">
                  <label>Azure Region</label>
                  <select className="zenith-select" value={config.azure_location} onChange={e => updateConfig('azure_location', e.target.value)}>
                    <option value="eastus">East US</option>
                    <option value="westeurope">West Europe</option>
                    <option value="southeastasia">Southeast Asia</option>
                  </select>
                </div>
                <div className="config-field">
                  <label>Resource Group</label>
                  <input
                    type="text"
                    value={config.resource_group_name}
                    onChange={e => updateConfig('resource_group_name', e.target.value)}
                  />
                </div>
                {config.enable_azure_storage && (
                  <>
                    <div className="config-field">
                      <label>Storage Account Name</label>
                      <input
                        type="text"
                        value={config.storage_account_name}
                        onChange={e => updateConfig('storage_account_name', e.target.value)}
                        placeholder="zenithstorage01"
                      />
                    </div>
                    <div className="config-field">
                      <label>Container Name</label>
                      <input
                        type="text"
                        value={config.container_name}
                        onChange={e => updateConfig('container_name', e.target.value)}
                      />
                    </div>
                  </>
                )}
                {config.enable_azure_vm && (
                  <>
                    <div className="config-field">
                      <label>VM Size</label>
                      <select className="zenith-select" value={config.vm_size} onChange={e => updateConfig('vm_size', e.target.value)}>
                        <option value="Standard_B1s">Standard_B1s (Free tier eligible)</option>
                        <option value="Standard_B2s">Standard_B2s</option>
                      </select>
                    </div>
                    <div className="config-field">
                      <label>VM Name</label>
                      <input
                        type="text"
                        value={config.instance_name}
                        onChange={e => updateConfig('instance_name', e.target.value)}
                        placeholder="zenith-linux-vm"
                      />
                    </div>
                  </>
                )}
                {config.enable_azure_monitor && (
                  <div className="config-field">
                    <label>Alert Email</label>
                    <input
                      type="email"
                      value={config.alarm_email}
                      onChange={e => updateConfig('alarm_email', e.target.value)}
                      placeholder="admin@example.com"
                    />
                  </div>
                )}
                {config.enable_cosmos && (
                  <>
                    <div className="config-field">
                      <label>Cosmos DB Account Name</label>
                      <input
                        type="text"
                        value={config.cosmos_account_name}
                        onChange={e => updateConfig('cosmos_account_name', e.target.value)}
                        placeholder="zenithcosmos01"
                      />
                    </div>
                    <div className="config-field">
                      <label>Cosmos Database Name</label>
                      <input
                        type="text"
                        value={config.cosmos_database_name}
                        onChange={e => updateConfig('cosmos_database_name', e.target.value)}
                        placeholder="zenith-db"
                      />
                    </div>
                  </>
                )}
              </>
            )}

            {config.enable_ec2 && (
              <>
                <div className="config-field">
                  <label>Instance Type</label>
                  <select className="zenith-select" value={config.instance_type} onChange={e => updateConfig('instance_type', e.target.value)}>
                    <option value="t2.micro">t2.micro (Free Tier)</option>
                    <option value="t3.micro">t3.micro (Free Tier)</option>
                    <option value="t2.small">t2.small ($16.79/mo)</option>
                    <option value="t2.medium">t2.medium ($33.58/mo)</option>
                    <option value="t3.small">t3.small ($15.18/mo)</option>
                    <option value="t3.medium">t3.medium ($30.37/mo)</option>
                  </select>
                </div>
                <div className="config-field">
                  <label>Instance Name</label>
                  <input
                    type="text"
                    value={config.instance_name}
                    onChange={e => updateConfig('instance_name', e.target.value)}
                    placeholder="zenith-app-server"
                  />
                </div>
              </>
            )}

            {config.enable_s3 && (
              <div className="config-field">
                <label>S3 Bucket Name (globally unique)</label>
                <input
                  type="text"
                  value={config.bucket_name}
                  onChange={e => updateConfig('bucket_name', e.target.value)}
                  onBlur={e => {
                    const sanitized = e.target.value.trim().toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9.-]/g, '').replace(/-+/g, '-').replace(/^[-.]+|[-.]+$/g, '').slice(0, 63);
                    if (sanitized !== config.bucket_name) {
                      updateConfig('bucket_name', sanitized);
                    }
                  }}
                  placeholder="my-testing-bucket-for-zenith"
                  pattern="[a-z0-9][a-z0-9.\-]{1,61}[a-z0-9]"
                  title="Lowercase letters, numbers, dots, and hyphens only (3–63 characters)"
                />
                <p className="config-field-hint">Use lowercase only — no spaces or uppercase (e.g. my-zenith-bucket-2026).</p>
              </div>
            )}

            {config.enable_iam && (
              <div className="config-field">
                <label>IAM Role Name</label>
                <input
                  type="text"
                  value={config.role_name}
                  onChange={e => updateConfig('role_name', e.target.value)}
                  placeholder="zenith-app-role"
                />
              </div>
            )}

            {config.enable_dynamodb && (
              <>
                <div className="config-field">
                  <label>DynamoDB Table Name</label>
                  <input
                    type="text"
                    value={config.dynamodb_table_name}
                    onChange={e => updateConfig('dynamodb_table_name', e.target.value)}
                    placeholder="zenith-data"
                  />
                </div>
                <div className="config-field">
                  <label>Hash Key Name</label>
                  <input
                    type="text"
                    value={config.dynamodb_hash_key}
                    onChange={e => updateConfig('dynamodb_hash_key', e.target.value)}
                    placeholder="id"
                  />
                </div>
              </>
            )}

            {config.enable_cloudwatch && (
              <div className="config-field">
                <label>Alarm Email</label>
                <input
                  type="email"
                  value={config.alarm_email}
                  onChange={e => updateConfig('alarm_email', e.target.value)}
                  placeholder="alerts@example.com"
                />
              </div>
            )}

            {csp === 'AWS' && config.enable_billing && (
              <>
                <div className="config-field">
                  <label>Budget Limit (USD/month)</label>
                  <input
                    type="text"
                    value={config.budget_limit}
                    onChange={e => updateConfig('budget_limit', e.target.value)}
                    placeholder="1"
                  />
                </div>
                <div className="config-field">
                  <label>Budget Alert Email</label>
                  <input
                    type="email"
                    value={config.budget_email}
                    onChange={e => updateConfig('budget_email', e.target.value)}
                    placeholder="billing@example.com"
                  />
                </div>
              </>
            )}
          </div>

          <div className="provision-actions">
            <button className="btn-provision secondary" onClick={prevStep}>← Back</button>
            <button className="btn-provision primary" onClick={nextStep}>
              Next: Review →
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Review */}
      {step === 3 && (
        <div>
          <div className="section-header">
            <h3>Review before build</h3>
            <p>Plain-English summary, security policies, and estimated costs.</p>
          </div>

          <PlainEnglishReview summary={reviewSummary} loading={reviewSummaryLoading} />

          {loading && (
            <div className="provision-loading">
              <div className="provision-spinner" />
              <span>Running policy check & cost estimate...</span>
            </div>
          )}

          {/* Policy Results */}
          {policyResult && (
            <div className="policy-results">
              <h3>🛡️ Policy Check</h3>

              {policyResult.blocks && policyResult.blocks.length > 0 && (
                <div>
                  <span className="policy-badge block">🚫 {policyResult.blocks.length} Blocked</span>
                  {policyResult.blocks.map((b, i) => (
                    <div key={i} className="policy-item block">
                      <div>
                        <div className="policy-item-name">{b.rule_name}</div>
                        <div className="policy-item-desc">{b.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {policyResult.warnings && policyResult.warnings.length > 0 && (
                <div style={{ marginTop: '1rem' }}>
                  <span className="policy-badge warning">⚠️ {policyResult.warnings.length} Warnings</span>
                  {policyResult.warnings.map((w, i) => (
                    <div key={i} className="policy-item warning">
                      <div>
                        <div className="policy-item-name">{w.rule_name}</div>
                        <div className="policy-item-desc">{w.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {policyResult.can_deploy && (
                <span className="policy-badge passed">✅ All security checks passed</span>
              )}
            </div>
          )}

          {/* Cost Estimate */}
          {costEstimate && costEstimate.resources && costEstimate.resources.length > 0 && (
            <div>
              <h3 style={{ color: 'var(--text-primary, #fff)', marginBottom: '1rem', fontSize: '1.1rem' }}>
                💰 Cost Estimate
              </h3>
              <table className="cost-table">
                <thead>
                  <tr>
                    <th>Resource</th>
                    <th>Monthly Cost</th>
                    <th>Note</th>
                  </tr>
                </thead>
                <tbody>
                  {costEstimate.resources.map((r, i) => (
                    <tr key={i}>
                      <td>{r.name}</td>
                      <td>${r.monthly_cost}</td>
                      <td className="cost-note">{r.note || ''}</td>
                    </tr>
                  ))}
                  <tr>
                    <td><strong>Total</strong></td>
                    <td className="cost-total">${costEstimate.total_monthly_cost}/month</td>
                    <td className="cost-note">{costEstimate.currency}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          <div className="provision-actions">
            <button className="btn-provision secondary" onClick={prevStep}>← Back</button>
            <button
              className="btn-provision primary"
              disabled={!policyResult || !policyResult.can_deploy || loading}
              onClick={nextStep}
            >
              {policyResult && !policyResult.can_deploy
                ? '🚫 Fix policy violations first'
                : 'Next: Run Plan →'}
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Build */}
      {step === 4 && (
        <div>
          <div className="section-header">
            <h3>{engineLabel} plan &amp; apply</h3>
            <p>Review the execution plan, then apply to create real {csp} resources.</p>
          </div>

          {loading && !planOutput && (
            <div className="provision-loading">
              <div className="provision-spinner" />
              <span>Running {engineLabel} plan…</span>
            </div>
          )}

          {planOutput && (
            <div className="terraform-terminal" ref={terminalRef}>
              {planOutput.split('\n').map((line, i) => {
                let cls = 'tf-line';
                if (line.trim().startsWith('+')) cls += ' tf-add';
                else if (line.trim().startsWith('-')) cls += ' tf-remove';
                else if (line.trim().startsWith('~')) cls += ' tf-change';
                return <div key={i} className={cls}>{line || ' '}</div>;
              })}
            </div>
          )}

          <div className="provision-actions">
            <button className="btn-provision secondary" onClick={() => setStep(0)}>
              ← Start Over
            </button>
            {deploymentId && (
              <>
                <button
                  type="button"
                  className="btn-provision secondary"
                  onClick={downloadTerraformExport}
                  disabled={!planReady}
                >
                  Download Terraform
                </button>
                <button
                  className="btn-provision primary"
                  disabled={loading || !planReady}
                  title={!planReady ? `Wait for ${engineLabel} plan to finish successfully` : undefined}
                  onClick={runApply}
                  type="button"
                >
                  {loading && planReady ? (
                    <><div className="provision-spinner" style={{ width: 16, height: 16 }} /> Applying on {csp}…</>
                  ) : planReady ? (
                    '🚀 Apply — Create Resources'
                  ) : (
                    '⏳ Waiting for plan…'
                  )}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
