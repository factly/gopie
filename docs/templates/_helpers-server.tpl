{{/*
Expand the name of the chart.
*/}}
{{- define "gopie.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "gopie.fullname" -}}
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
gopie server name
*/}}
{{- define "server.name" -}}
{{- printf "%s-%s" (include "gopie.fullname" .) .Values.server.name | trunc 63 | trimSuffix "-" -}}
{{- end }}


{{/* 
namespace to be release namespace
*/}}
{{- define "gopie.namespace" -}}
{{- .Release.Namespace -}}
{{ end }}

{{/* 
gopie server common labels
*/}}
{{- define "server.labels" -}}
{{ include "server.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Version }}
{{- with .Values.server.extraLabels }}
{{ toYaml . }}
{{ end }}
{{ end }}

{{/* 
gopie server annotations
*/}}
{{- define "server.annotations" -}}
{{- with .Values.server.annotations }}
{{ toYaml . }}
{{ end }}
{{ end }}

{{/*
gopie server Selector labels
*/}}
{{- define "server.selectorLabels" -}}
app.kubernetes.io/component: {{ .Values.server.name }}
app.kubernetes.io/name: {{ include "gopie.fullname" . }}-{{ .Values.server.name }}
{{- end }}

{{/* 
gopie server pod labels
*/}}
{{- define "server.PodLabels" -}}
{{ include "server.labels" . }}
{{- with .Values.server.extraPodLabels }}
{{ toYaml . }}
{{ end }}
{{ end }}

{{/* 
gopie server pod annotations
*/}}
{{- define "server.PodAnnotations" -}}
{{- with .Values.server.Podannotations }}
{{ toYaml . }}
{{ end }}
{{ end }}

{{/*
Create service account to use for gopie server
*/}}
{{- define "server.serviceAccountName" -}}
{{- if .Values.server.serviceAccount.create }}
{{- default (include "server.name" .) .Values.server.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.server.serviceAccount.name }}
{{- end }}
{{- end }}



{{/*
gopie web section
*/}}


{{/*
gopie web name
*/}}
{{- define "web.name" -}}
{{- printf "%s-%s" (include "gopie.fullname" .) .Values.web.name | trunc 63 | trimSuffix "-" -}}
{{- end }}


{{/* 
gopie web common labels
*/}}
{{- define "web.labels" -}}
{{ include "web.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Version }}
{{- with .Values.web.extraLabels }}
{{ toYaml . }}
{{ end }}
{{ end }}

{{/* 
gopie web annotations
*/}}
{{- define "web.annotations" -}}
{{- with .Values.web.annotations }}
{{ toYaml . }}
{{ end }}
{{ end }}

{{/*
gopie web Selector labels
*/}}
{{- define "web.selectorLabels" -}}
app.kubernetes.io/component: {{ .Values.web.name }}
app.kubernetes.io/name: {{ include "gopie.fullname" . }}-{{ .Values.web.name }}
{{- end }}

{{/* 
gopie web pod labels
*/}}
{{- define "web.PodLabels" -}}
{{ include "web.labels" . }}
{{- with .Values.web.extraPodLabels }}
{{ toYaml . }}
{{ end }}
{{ end }}

{{/* 
gopie web pod annotations
*/}}
{{- define "web.PodAnnotations" -}}
{{- with .Values.web.Podannotations }}
{{ toYaml . }}
{{ end }}
{{ end }}

{{/*
Create service account to use for gopie web
*/}}
{{- define "web.serviceAccountName" -}}
{{- if .Values.web.serviceAccount.create }}
{{- default (include "web.name" .) .Values.web.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.web.serviceAccount.name }}
{{- end }}
{{- end }}


{{/*
gopie chatserver section
*/}}


{{/*
gopie chatserver name
*/}}
{{- define "chatserver.name" -}}
{{- printf "%s-%s" (include "gopie.fullname" .) .Values.chatserver.name | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/* 
gopie chatserver namespace
*/}}
{{- define "chatserver.namespace" -}}
{{- .Release.Namespace -}}
{{ end }}

{{/* 
gopie chatserver common labels
*/}}
{{- define "chatserver.labels" -}}
{{ include "chatserver.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Version }}
{{- with .Values.chatserver.extraLabels }}
{{ toYaml . }}
{{ end }}
{{ end }}

{{/* 
gopie chatserver annotations
*/}}
{{- define "chatserver.annotations" -}}
{{- with .Values.chatserver.annotations }}
{{ toYaml . }}
{{ end }}
{{ end }}

{{/*
gopie chatserver Selector labels
*/}}
{{- define "chatserver.selectorLabels" -}}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/name: {{ include "chatserver.name" . }}
{{- end }}

{{/* 
gopie chatserver pod labels
*/}}
{{- define "chatserver.PodLabels" -}}
{{ include "chatserver.labels" . }}
{{- with .Values.chatserver.extraPodLabels }}
{{ toYaml . }}
{{ end }}
{{ end }}

{{/* 
gopie chatserver pod annotations
*/}}
{{- define "chatserver.PodAnnotations" -}}
{{- with .Values.chatserver.Podannotations }}
{{ toYaml . }}
{{ end }}
{{ end }}

{{/*
Create service account to use for gopie chatserver
*/}}
{{- define "chatserver.serviceAccountName" -}}
{{- if .Values.chatserver.serviceAccount.create }}
{{- default (include "chatserver.name" .) .Values.chatserver.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.chatserver.serviceAccount.name }}
{{- end }}
{{- end }}