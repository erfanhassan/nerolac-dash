{{/*
Expand the name of the chart.
*/}}
{{- define "nerolac-portal.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "nerolac-portal.fullname" -}}
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
Frontend full name
*/}}
{{- define "nerolac-portal.frontend.fullname" -}}
{{- printf "%s-frontend" (include "nerolac-portal.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Backend full name
*/}}
{{- define "nerolac-portal.backend.fullname" -}}
{{- printf "%s-backend" (include "nerolac-portal.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "nerolac-portal.labels" -}}
helm.sh/chart: {{ include "nerolac-portal.name" . }}-{{ .Chart.Version | replace "+" "_" }}
{{ include "nerolac-portal.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: nerolac-portal
{{- end }}

{{/*
Selector labels
*/}}
{{- define "nerolac-portal.selectorLabels" -}}
app.kubernetes.io/name: {{ include "nerolac-portal.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Frontend selector labels
*/}}
{{- define "nerolac-portal.frontend.selectorLabels" -}}
{{ include "nerolac-portal.selectorLabels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Backend selector labels
*/}}
{{- define "nerolac-portal.backend.selectorLabels" -}}
{{ include "nerolac-portal.selectorLabels" . }}
app.kubernetes.io/component: backend
{{- end }}
