{{/*
Expand the name of the chart.
*/}}
{{- define "alphatrion.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "alphatrion.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "alphatrion.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "alphatrion.labels" -}}
helm.sh/chart: {{ include "alphatrion.chart" . }}
{{ include "alphatrion.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "alphatrion.selectorLabels" -}}
app.kubernetes.io/name: {{ include "alphatrion.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Server specific labels
*/}}
{{- define "alphatrion.server.labels" -}}
{{ include "alphatrion.labels" . }}
app.kubernetes.io/component: server
{{- end }}

{{/*
Server selector labels
*/}}
{{- define "alphatrion.server.selectorLabels" -}}
{{ include "alphatrion.selectorLabels" . }}
app.kubernetes.io/component: server
{{- end }}

{{/*
Server fullname
*/}}
{{- define "alphatrion.server.fullname" -}}
{{- printf "%s-server" (include "alphatrion.fullname" .) }}
{{- end }}

{{/*
Dashboard specific labels
*/}}
{{- define "alphatrion.dashboard.labels" -}}
{{ include "alphatrion.labels" . }}
app.kubernetes.io/component: dashboard
{{- end }}

{{/*
Dashboard selector labels
*/}}
{{- define "alphatrion.dashboard.selectorLabels" -}}
{{ include "alphatrion.selectorLabels" . }}
app.kubernetes.io/component: dashboard
{{- end }}

{{/*
Dashboard fullname
*/}}
{{- define "alphatrion.dashboard.fullname" -}}
{{- printf "%s-dashboard" (include "alphatrion.fullname" .) }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "alphatrion.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "alphatrion.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
PostgreSQL host
*/}}
{{- define "alphatrion.postgresql.host" -}}
{{- .Values.postgresql.host }}
{{- end }}

{{/*
PostgreSQL port
*/}}
{{- define "alphatrion.postgresql.port" -}}
{{- .Values.postgresql.port }}
{{- end }}

{{/*
PostgreSQL database
*/}}
{{- define "alphatrion.postgresql.database" -}}
{{- .Values.postgresql.database }}
{{- end }}

{{/*
PostgreSQL username
*/}}
{{- define "alphatrion.postgresql.username" -}}
{{- .Values.postgresql.username }}
{{- end }}

{{/*
PostgreSQL password secret name
*/}}
{{- define "alphatrion.postgresql.secretName" -}}
{{- if .Values.postgresql.existingSecret }}
{{- .Values.postgresql.existingSecret }}
{{- else }}
{{- include "alphatrion.server.fullname" . }}
{{- end }}
{{- end }}

{{/*
PostgreSQL password secret key
*/}}
{{- define "alphatrion.postgresql.secretKey" -}}
{{- "postgres-password" }}
{{- end }}

{{/*
ClickHouse host
*/}}
{{- define "alphatrion.clickhouse.host" -}}
{{- .Values.clickhouse.host }}
{{- end }}

{{/*
ClickHouse secret name
*/}}
{{- define "alphatrion.clickhouse.secretName" -}}
{{- if .Values.clickhouse.existingSecret }}
{{- .Values.clickhouse.existingSecret }}
{{- else }}
{{- printf "%s-clickhouse" (include "alphatrion.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Docker Registry secret name
*/}}
{{- define "alphatrion.registry.secretName" -}}
{{- if .Values.registry.existingSecret }}
{{- .Values.registry.existingSecret }}
{{- else }}
{{- printf "%s-registry" (include "alphatrion.fullname" .) }}
{{- end }}
{{- end }}
