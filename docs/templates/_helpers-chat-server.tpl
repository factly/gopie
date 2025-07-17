
# {{/* 
# namespace to be release namespace
# */}}
# {{- define "dataful-agent.namespace" -}}
# {{- .Release.Namespace -}}
# {{ end }}

# {{/* 
# rill common labels
# */}}
# {{- define "dataful-agent.labels" -}}
# {{ include "dataful-agent.selectorLabels" . }}
# app.kubernetes.io/managed-by: {{ .Release.Service }}
# helm.sh/chart: {{ .Chart.Version }}
# {{- with .Values.extraLabels }}
# {{ toYaml . }}
# {{ end }}
# {{ end }}

# {{/* 
# rill annotations
# */}}
# {{- define "dataful-agent.annotations" -}}
# {{- with .Values.annotations }}
# {{ toYaml . }}
# {{ end }}
# {{ end }}

# {{/*
# rill Selector labels
# */}}
# {{- define "dataful-agent.selectorLabels" -}}
# app.kubernetes.io/instance: {{ .Release.Name }}
# app.kubernetes.io/name: {{ include "dataful-agent.name" . }}
# {{- end }}

# {{/* 
# rill pod labels
# */}}
# {{- define "dataful-agent.PodLabels" -}}
# {{ include "dataful-agent.labels" . }}
# {{- with .Values.extraPodLabels }}
# {{ toYaml . }}
# {{ end }}
# {{ end }}

# {{/* 
# rill pod annotations
# */}}
# {{- define "dataful-agent.PodAnnotations" -}}
# {{- with .Values.Podannotations }}
# {{ toYaml . }}
# {{ end }}
# {{ end }}

# {{/*
# Create service account to use for rill
# */}}
# {{- define "dataful-agent.serviceAccountName" -}}
# {{- if .Values.serviceAccount.create }}
# {{- default (include "dataful-agent.fullname" .) .Values.serviceAccount.name }}
# {{- else }}
# {{- default "default" .Values.serviceAccount.name }}
# {{- end }}
# {{- end }}