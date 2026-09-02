param(
    [string]$ProjectId = "irfan-374115",
    [string]$Bucket = "irfan-374115-fpl-snapshots"
)

# Creates the identity used by the private control API. It deliberately does
# not create credentials or secrets; those values must be supplied by the
# owner after rotating the legacy Telegram token.
$ErrorActionPreference = "Stop"
$ProjectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)"
$Account = "fpl-control-api@$ProjectId.iam.gserviceaccount.com"

if (-not (gcloud iam service-accounts list --project $ProjectId --filter "email:$Account" --format="value(email)")) {
    gcloud iam service-accounts create "fpl-control-api" --display-name "FPL private control API" --project $ProjectId
}

gcloud storage buckets add-iam-policy-binding "gs://$Bucket" --member "serviceAccount:$Account" --role roles/storage.objectAdmin
gcloud iam service-accounts add-iam-policy-binding $Account --project $ProjectId --member "serviceAccount:$ProjectNumber-compute@developer.gserviceaccount.com" --role roles/iam.serviceAccountUser

Write-Output "Provisioned $Account. Add Secret Manager bindings only for the named control secrets after creating them."
