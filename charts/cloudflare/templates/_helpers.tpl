{{/*
Common chart name and labels
*/}}

{{- define "cloudflare.name" -}}
{{ .Chart.Name }}
{{- end -}}

{{- define "cloudflare.labels" -}}
app.kubernetes.io/name: {{ include "cloudflare.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: Helm
app.kubernetes.io/component: tunnel
{{- end -}}

{{- define "cloudflare.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cloudflare.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
