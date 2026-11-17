{{- define "lsk-gateway.validate" -}}
{{- if not .Values.image.repository -}}
{{- fail "image.repository must be a reviewed ECR repository" -}}
{{- end -}}
{{- if not regexMatch "^sha256:[0-9a-f]{64}$" .Values.image.digest -}}
{{- fail "image.digest must be an immutable SHA256 digest" -}}
{{- end -}}
{{- if ne .Values.env.stage "poc" -}}
{{- fail "pilot/production are blocked until enterprise identity and persistence are implemented" -}}
{{- end -}}
{{- if ne (toString .Values.env.enableDemoWrites) "false" -}}
{{- fail "this EKS chart prohibits synthetic demo writes until a managed command store exists" -}}
{{- end -}}
{{- if not .Values.existingSecretName -}}
{{- fail "existingSecretName must reference an independently provisioned Kubernetes Secret" -}}
{{- end -}}
{{- if not .Values.serviceAccount.name -}}
{{- fail "serviceAccount.name is required" -}}
{{- end -}}
{{- if ne .Values.service.type "ClusterIP" -}}
{{- fail "only ClusterIP is permitted in the POC chart" -}}
{{- end -}}
{{- if ne (int .Values.replicaCount) 1 -}}
{{- fail "POC gateway is not safe to scale without durable command state: replicaCount must equal 1" -}}
{{- end -}}
{{- end -}}
