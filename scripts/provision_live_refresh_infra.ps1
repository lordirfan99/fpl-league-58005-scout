param(
    [string]$ProjectId = "irfan-374115",
    [string]$Region = "us-central1",
    [string]$Bucket = "irfan-374115-fpl-snapshots"
)

$ErrorActionPreference = "Stop"
$ProjectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)"
$SchedulerServiceAccount = "fpl-live-refresh-scheduler@$ProjectId.iam.gserviceaccount.com"
$JobName = "fpl-live-league-refresh"
$ServiceName = "fpl-scheduled-tasks"

gcloud services enable run.googleapis.com cloudscheduler.googleapis.com --project $ProjectId

foreach ($Account in @(@{ Email = $SchedulerServiceAccount; Name = "FPL live refresh scheduler" })) {
    $Existing = gcloud iam service-accounts list --project $ProjectId --filter "email:$($Account.Email)" --format="value(email)"
    if (-not $Existing) {
        $Id = $Account.Email.Split('@')[0]
        gcloud iam service-accounts create $Id --display-name $Account.Name --project $ProjectId
    }
}

$ServiceUrl = gcloud run services describe $ServiceName --region $Region --project $ProjectId --format="value(status.url)" 2>$null
if (-not $ServiceUrl) {
    Write-Output "Deploy request-based service '$ServiceName', then run this script again."
    exit 0
}

# Scheduler invokes only the request-based service. The legacy Job remains a
# manual recovery option but is no longer scheduled.
gcloud run services add-iam-policy-binding $ServiceName --region $Region --member "serviceAccount:$SchedulerServiceAccount" --role roles/run.invoker --project $ProjectId
gcloud iam service-accounts add-iam-policy-binding $SchedulerServiceAccount --member "serviceAccount:service-$ProjectNumber@gcp-sa-cloudscheduler.iam.gserviceaccount.com" --role roles/iam.serviceAccountTokenCreator --project $ProjectId

$TaskUri = "$ServiceUrl/tasks/live-refresh"
$ExistingScheduler = gcloud scheduler jobs list --location $Region --project $ProjectId --filter "name:$JobName" --format="value(name)"
if ($ExistingScheduler) {
    gcloud scheduler jobs update http $JobName --location $Region --schedule "*/30 * * * *" --time-zone "Etc/UTC" --uri $TaskUri --http-method POST --oidc-service-account-email $SchedulerServiceAccount --oidc-token-audience $ServiceUrl --attempt-deadline "1800s" --max-retry-attempts 3 --project $ProjectId
} else {
    gcloud scheduler jobs create http $JobName --location $Region --schedule "*/30 * * * *" --time-zone "Etc/UTC" --uri $TaskUri --http-method POST --oidc-service-account-email $SchedulerServiceAccount --oidc-token-audience $ServiceUrl --attempt-deadline "1800s" --max-retry-attempts 3 --project $ProjectId
}

Write-Output "Provisioned request-based $JobName trigger."
