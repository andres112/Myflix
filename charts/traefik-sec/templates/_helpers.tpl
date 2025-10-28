{{/*
Return a fully qualified name for resources
*/}}
{{- define "traefik-sec.fullname" -}}
{{- printf "%s-%s" .Release.Name "traefik-sec" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "traefik-sec.labels" -}}
app.kubernetes.io/name: traefik-sec
app.kubernetes.io/instance: {{ .Release.Name }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}
