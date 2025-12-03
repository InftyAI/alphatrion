// ============================================
// Projects
// ============================================
export const LIST_PROJECTS = `
  query ListProjects($page: Int, $pageSize: Int) {
    projects(page: $page, pageSize: $pageSize) {
      id
      name
      description
      createdAt
      updatedAt
    }
  }
`;

export const GET_PROJECT = `
  query GetProject($id: String!) {
    project(id: $id) {
      id
      name
      description
      createdAt
      updatedAt
    }
  }
`;

// ============================================
// Experiments
// ============================================
export const LIST_EXPERIMENTS = `
  query ListExperiments($projectId: String!, $page: Int, $pageSize: Int) {
    experiments(projectId: $projectId, page: $page, pageSize: $pageSize) {
      id
      projectId
      name
      description
      meta
      createdAt
      updatedAt
    }
  }
`;

export const GET_EXPERIMENT = `
  query GetExperiment($id: String!) {
    experiment(id: $id) {
      id
      projectId
      name
      description
      meta
      createdAt
      updatedAt
    }
  }
`;

// ============================================
// Trials
// ============================================
export const LIST_TRIALS = `
  query ListTrials($experimentId: String!, $page: Int, $pageSize: Int) {
    trials(experimentId: $experimentId, page: $page, pageSize: $pageSize) {
      id
      experimentId
      projectId
      name
      description
      meta
      params
      duration
      status
      createdAt
      updatedAt
    }
  }
`;

export const GET_TRIAL = `
  query GetTrial($id: String!) {
    trial(id: $id) {
      id
      experimentId
      projectId
      name
      description
      meta
      params
      duration
      status
      createdAt
      updatedAt
    }
  }
`;

// ============================================
// Runs
// ============================================
export const LIST_RUNS = `
  query ListRuns($trialId: String!, $page: Int, $pageSize: Int) {
    runs(trialId: $trialId, page: $page, pageSize: $pageSize) {
      id
      trialId
      projectId
      experimentId
      meta
      status
      createdAt
    }
  }
`;

export const GET_RUN = `
  query GetRun($id: String!) {
    run(id: $id) {
      id
      trialId
      projectId
      experimentId
      meta
      status
      createdAt
    }
  }
`;

// ============================================
// Metrics (for Trial Curve)
// ============================================
export const LIST_TRIAL_METRICS = `
  query ListTrialMetrics($trialId: String!, $page: Int, $pageSize: Int) {
    trialMetrics(trialId: $trialId, page: $page, pageSize: $pageSize) {
      id
      key
      value
      projectId
      experimentId
      trialId
      runId
      step
      createdAt
    }
  }
`;