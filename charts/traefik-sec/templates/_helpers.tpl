{{/*
Return a fully qualified name for resources
*/}}
{{- define "traefik-sec.fullname" -}}
traefik-sec
{{- end -}}

{{/*
Common labels
*/}}
{{- define "traefik-sec.labels" -}}
app.kubernetes.io/name: traefik-sec
app.kubernetes.io/instance: {{ .Release.Name }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}
