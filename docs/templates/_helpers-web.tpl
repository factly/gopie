# {{/*
# gopie web only
# */}}
# {{- define "gopie-web.name" -}}
# {{- printf "%s-%s" (include "gopie.fullname" .) .Values.web.name | trunc 63 | trimSuffix "-" -}}
# {{- end }}


# {{/* 
# gopie web common labels
# */}}
# {{- define "gopie-web.labels" -}}
# {{ include "gopie-web.selectorLabels" . }}
# app.kubernetes.io/managed-by: {{ .Release.Service }}
# helm.sh/chart: {{ .Chart.Version }}
# {{- with .Values.web.extraLabels }}
# {{ toYaml . }}
# {{ end }}
# {{ end }}

# {{/* 
# gopie web annotations
# */}}
# {{- define "gopie-web.annotations" -}}
# {{- with .Values.web.annotations }}
# {{ toYaml . }}
# {{ end }}
# {{ end }}

# {{/*
# gopie web Selector labels
# */}}
# {{- define "gopie-web.selectorLabels" -}}
# app.kubernetes.io/component: {{ .Values.web.name }}
# app.kubernetes.io/name: {{ include "gopie.fullname" . }}-{{ .Values.web.name }}
# {{- end }}

# {{/* 
# gopie web pod labels
# */}}
# {{- define "gopie-web.PodLabels" -}}
# {{ include "gopie-web.labels" . }}
# {{- with .Values.web.extraPodLabels }}
# {{ toYaml . }}
# {{ end }}
# {{ end }}

# {{/* 
# gopie web pod annotations
# */}}
# {{- define "gopie-web.PodAnnotations" -}}
# {{- with .Values.web.Podannotations }}
# {{ toYaml . }}
# {{ end }}
# {{ end }}

# {{/*
# Create service account to use for gopie web
# */}}
# {{- define "gopie-web.serviceAccountName" -}}
# {{- if .Values.web.serviceAccount.create }}
# {{- default (include "gopie-web.name" .) .Values.web.serviceAccount.name }}
# {{- else }}
# {{- default "default" .Values.web.serviceAccount.name }}
# {{- end }}
# {{- end }}