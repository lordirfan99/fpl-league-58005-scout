param(
    [string]$ProjectId = "irfan-374115",
    [string]$Region = "us-central1",
    [string]$Bucket = "irfan-374115-fpl-snapshots"
)

# Provisions the GCP side of the scheduled tasks that replaced the GitHub
# Actions crons (refresh-fixtures, capture-journal, refresh-gameweek,
# monitor-production). The Cloud Run Jobs themselves are created by the
# cloudbuild.api.yaml deployment; run this script once before that deploy to
# create identities, and again afterwards to bind the Cloud Scheduler triggers.

$ErrorActionPreference = "Stop"
$ProjectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)"
$RuntimeServiceAccount = "fpl-scheduled-tasks@$ProjectId.iam.gserviceaccount.com"
$SchedulerServiceAccount = "fpl-scheduled-tasks-scheduler@$ProjectId.iam.gserviceaccount.com"

# Scheduler trigger name -> request-based task and cron schedule (UTC).
# The old Cloud Run Jobs remain available for manual recovery, but recurring
# calls use a service so short self-gated requests do not incur a one-minute
# Cloud Run Job minimum.
$ServiceName = "fpl-scheduled-tasks"
$Triggers = [ordered]@{
    "fpl-refresh-fixtures"       = @{ Task = "fixtures"; Schedule = "17 * * * *" }
    "fpl-capture-journal"        = @{ Task = "capture-journal"; Schedule = "17 * * * *" }
    "fpl-refresh-gameweek"       = @{ Task = "finalize-gameweek"; Schedule = "23 * * * *" }
    "fpl-decision-refresh"       = @{ Task = "decision-refresh"; Schedule = "27 * * * *" }
    "fpl-decision-final-window"  = @{ Task = "decision-final-window"; Schedule = "*/15 * * * *" }
    "fpl-monitor"                = @{ Task = "monitor"; Schedule = "*/30 * * * *" }
}

gcloud services enable run.googleapis.com cloudscheduler.googleapis.com --project $ProjectId

foreach ($Account in @(
    @{ Email = $RuntimeServiceAccount; Name = "FPL scheduled tasks runtime" },
    @{ Email = $SchedulerServiceAccount; Name = "FPL scheduled tasks scheduler" }
)) {
    $Existing = gcloud iam service-accounts list --project $ProjectId --filter "email:$($Account.Email)" --format="value(email)"
    if (-not $Existing) {
        $Id = $Account.Email.Split('@')[0]
        gcloud iam service-accounts create $Id --display-name $Account.Name --project $ProjectId
    }
}

# The tasks read and write only the shared snapshot bucket.
gcloud storage buckets add-iam-policy-binding "gs://$Bucket" --member "serviceAccount:$RuntimeServiceAccount" --role roles/storage.objectAdmin

# Cloud Build deploys the jobs on each production API deployment and must be
# allowed to attach the runtime identity.
gcloud iam service-accounts add-iam-policy-binding $RuntimeServiceAccount --member "serviceAccount:$ProjectNumber-compute@developer.gserviceaccount.com" --role roles/iam.serviceAccountUser --project $ProjectId

# The Scheduler service agent may mint OAuth tokens for the scheduler identity.
gcloud iam service-accounts add-iam-policy-binding $SchedulerServiceAccount --member "serviceAccount:service-$ProjectNumber@gcp-sa-cloudscheduler.iam.gserviceaccount.com" --role roles/iam.serviceAccountTokenCreator --project $ProjectId

$ServiceUrl = gcloud run services describe $ServiceName --region $Region --project $ProjectId --format="value(status.url)" 2>$null
if (-not $ServiceUrl) {
    Write-Output "Cloud Run service '$ServiceName' not deployed yet. Deploy the production branch, then run this script again."
    exit 0
}

# Scheduler may invoke only this private service.
gcloud run services add-iam-policy-binding $ServiceName --region $Region --member "serviceAccount:$SchedulerServiceAccount" --role roles/run.invoker --project $ProjectId

foreach ($TriggerName in $Triggers.Keys) {
    $Task = $Triggers[$TriggerName].Task
    $Schedule = $Triggers[$TriggerName].Schedule
    $TaskUri = "$ServiceUrl/tasks/$Task"
    $Existing = gcloud scheduler jobs list --location $Region --project $ProjectId --filter "name:$TriggerName" --format="value(name)"
    if ($Existing) {
        gcloud scheduler jobs update http $TriggerName --location $Region --schedule "$Schedule" --time-zone "Etc/UTC" --uri $TaskUri --http-method POST --oidc-service-account-email $SchedulerServiceAccount --oidc-token-audience $ServiceUrl --attempt-deadline "1800s" --max-retry-attempts 2 --project $ProjectId
    } else {
        gcloud scheduler jobs create http $TriggerName --location $Region --schedule "$Schedule" --time-zone "Etc/UTC" --uri $TaskUri --http-method POST --oidc-service-account-email $SchedulerServiceAccount --oidc-token-audience $ServiceUrl --attempt-deadline "1800s" --max-retry-attempts 2 --project $ProjectId
    }
    Write-Output "Provisioned request-based trigger '$TriggerName' -> $Task ($Schedule UTC)."
}

Write-Output ""
Write-Output "All request-based Cloud Scheduler triggers are provisioned."
Write-Output "The matching GitHub Actions workflows remain available as manual (workflow_dispatch) fallbacks."
