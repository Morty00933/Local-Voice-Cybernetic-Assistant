{{/*
Common labels
*/}}
{{- define "lvca.labels" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Selector labels for a component
*/}}
{{- define "lvca.selectorLabels" -}}
app.kubernetes.io/name: {{ .name }}
app.kubernetes.io/instance: {{ .instance }}
{{- end }}

{{/*
Ollama URL — internal or external
*/}}
{{- define "lvca.ollamaUrl" -}}
{{- if .Values.ollama.enabled -}}
http://{{ .Release.Name }}-ollama:{{ .Values.ollama.service.port }}
{{- else -}}
http://{{ .Values.externalServices.ollama }}
{{- end -}}
{{- end }}

{{/*
Qdrant URL
*/}}
{{- define "lvca.qdrantUrl" -}}
{{- if .Values.qdrant.enabled -}}
http://{{ .Release.Name }}-qdrant:{{ .Values.qdrant.service.port }}
{{- else -}}
http://{{ .Values.externalServices.qdrant }}
{{- end -}}
{{- end }}

{{/*
Redis URL
*/}}
{{- define "lvca.redisUrl" -}}
{{- if .Values.redis.enabled -}}
redis://{{ .Release.Name }}-redis:{{ .Values.redis.service.port }}/0
{{- else -}}
redis://{{ .Values.externalServices.redis }}/0
{{- end -}}
{{- end }}

{{/*
Security context (shared across all deployments)
*/}}
{{- define "lvca.securityContext" -}}
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  capabilities:
    drop: [ALL]
  allowPrivilegeEscalation: false
{{- end }}
