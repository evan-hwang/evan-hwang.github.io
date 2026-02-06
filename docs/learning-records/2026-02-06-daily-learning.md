---
layout: default
title: "2026-02-06 학습·작업 기록"
parent: 학습 기록
nav_order: 1
---

# 2026-02-06 학습·작업 기록

## 개요
오늘은 **세 가지 프로젝트**(`pd-disaggregation`, `project`, `recoblog`)에 대해 코드베이스 탐색, 설계 아이디어 도출, 그리고 Jekyll 블로그 포스트 작성을 진행했습니다.  
주요 주제는 다음과 같습니다.

1. **pd-disaggregation** - 연구 레포지토리 구조 파악 및 Prefill-Decode( PD ) 분산 추론 개념 정리  
2. **KAP GPU Inference Endpoint 자동 스케일링** - MVP 설계와 장기 아키텍처( KEDA + Kueue + Quota)  
3. **recoblog** - Jekyll + Just the Docs 테마 기반 블로그 레포지토리 탐색 (추후 포스트 작성 기반)

각 주제별 핵심 개념·배운 점을 정리하고, 실제 코드 예시(예: KEDA ScaledObject, PriorityClass) 를 간략히 제시합니다.

--- 

## 1️⃣ pd-disaggregation 프로젝트 탐색  

### 핵심 개념
| 키워드 | 설명 |
|--------|------|
| **PD (Prefill-Decode) Disaggregation** | LLM 추론을 **Prefill** 단계와 **Decode** 단계로 분리해 각각을 별도 GPU/네트워크 자원에 할당 → 파이프라인 지연 최소화 |
| **AWS EFA (Elastic Fabric Adapter)** | 400 Gbps 수준의 저지연 고대역폭 네트워킹, PD 실험에 필수 |
| **벤치마크 프레임워크** | `vLLM`(P0), `SGLang`(P1), `llm-d`(Reference) - 동일 모델(LLaMA-2-70B, TP=8) 에 대해 성능 비교 |
| **수집 메트릭** | GPU Util, Memory, SM 활동; EFA RX/TX; 네트워크 Throughput; TTFT / TPOT / Goodput |
| **읽기 전용(READ-ONLY) 모드** | Claude Code는 파일 **검색·읽기**만 가능 → 변경·작성 불가. 이를 염두에 두고 탐색 전략을 설계 |

### 배운 점
* **레포지토리 구조**: `PLAN.md`, `EXECUTE.md`, `docker/`, `research/` 등 크게 **계획·실행·컨테이너·연구** 폴더로 구분.  
* **문서 표준화**: `PLAN.md` → 설계·목표, `EXECUTE.md` → 실제 명령·결과·트러블슈팅(실패 기록 제외) 로 구분해 재현성을 높인다.  
* **읽기 전용 툴 활용**:  
  * `Glob` → 파일 목록 얻기 (`*.md`, `*.yaml`)  
  * `Grep` → 키워드("EFA", "vLLM") 검색  
  * `Read` → 핵심 스크립트(`run_experiment.sh`) 내용 확인  

> **예시** (`grep` 로 vLLM 설정 찾기)  
> ```bash
> $ grep -R "vllm" -n .
> 12:deployment.yaml:    image: ghcr.io/vllm/vllm:latest
> 45:run_experiment.sh:python -m vllm.entrypoint ...
> ```

---

## 2️⃣ KAP GPU Inference Endpoint 자동 스케일링 설계  

### 2-1. MVP 설계 (02:29 ~ 04:27)

#### 정책 옵션 비교
| 옵션 | 주요 특징 | 장점 | 단점 | 구현 난이도 |
|------|-----------|------|------|------------|
| **A. Global Resource Pool + 선착순** | 전체 GPU 10%(예: 8 GPU) 를 **ResourceQuota** 로 제한, 서비스별 `maxReplicaCount` 로 스케일링 | 구현 가장 간단 (KEDA + Quota) | 중요 서비스가 뒤처질 위험 | Low |
| **B. Priority-Based Pool + Preemption** | `PriorityClass`(production-critical 1000, production 500, default 100) 로 우선순위 부여, 필요 시 선점(preemption) | SLA-중요 워크로드 보장 | 복잡한 설정·테스트 필요 | Medium |
| **C. 2-Tier + Burst Pool (장기 모델)** | `Reserved` (60-70%), `Shared`, `Burst` (15-20%) 로 3-Tier 구조, `Kueue.borrowWithinCohort` 활용 | 탄력적 확장·자원 효율 극대화 | 설계·운영 부담 ↑ | High |

#### 핵심 구현 요소
1. **KEDA ScaledObject** - 메트릭 기반(예: GPU Util > 70%) 자동 스케일링  
2. **Kubernetes ResourceQuota** - 전체 클러스터 GPU 10% 한도 부여  
3. **PriorityClass** - 선점 가능 워크로드 정의  
4. **Kueue** - 워크로드 큐잉·자원 대여(borrow) 메커니즘  

#### 코드 스니펫  

*`PriorityClass` 정의*  
```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: production-critical
value: 1000
globalDefault: false
description: "Critical inference services (short-form video, etc.)"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: production
value: 500
globalDefault: false
description: "Standard production services"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: default
value: 100
globalDefault: true
description: "Fallback priority"
```

*`KEDA ScaledObject` (GPU Util 기준)*  
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: inference-scaler
spec:
  scaleTargetRef:
    name: inference-deployment
  pollingInterval: 30          # seconds
  cooldownPeriod: 180
  minReplicaCount: 1
  maxReplicaCount: 4           # 서비스별 오버라이드 가능
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc:9090
      metricName: gpu_utilization_percent
      query: |
        avg_over_time(gpu_utilization{namespace="inference"}[2m]) > 70
      threshold: "70"
```

*`ResourceQuota` (전체 GPU 10% 제한)*  
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: gpu-autoscale-quota
  namespace: autoscale-ns
spec:
  hard:
    nvidia.com/gpu: "8"   # 전체 클러스터 GPU 80 중 10%
```

### 2-2. 장기 아키텍처 (04:27 ~ 04:46)

#### 3-Tier 자원 풀 모델
```
┌─────────────────────────────────────────────────────────────┐
│                    KAP GPU Resource Pool                    │
├───────────────────────┬───────────────────────┬─────────────┤
│  RESERVED (60-70%)    │   SHARED (15-20%)     │   BURST (10-15%) │
│ - SLA 보장 (99.9%)    │ - 일반 서비스        │ - 스팟·프리미엄  │
│ - Eviction 금지      │ - 가변 maxReplica    │ - KEDA 자동 확장 │
└───────────────────────┴───────────────────────┴─────────────┘
```

* **Reserved** - 고정 할당량, Preemption 없음.  
* **Shared** - 다중 서비스가 풀을 공유, `Kueue` 가 `fair-sharing` 정책 적용.  
* **Burst** - 트래픽 급증 시 **borrowWithinCohort** 로 `Reserved` 혹은 `Shared` 로부터 일시적으로 GPU를 빌려 사용.  

#### 핵심 메커니즘
| 컴포넌트 | 역할 |
|----------|------|
| **Kueue** | `ClusterQueue`(Reserved, Shared, Burst) 정의, `Workload`-`Pod` 매핑, `Borrow` 정책 |
| **KEDA** | 메트릭(예: GPU Util, Queue Length) 기반 `ScaledObject` 로 Burst-Pool 자동 확장 |
| **Quota Controller** | 전체 GPU 10% 한도(Ops-level) 적용, `LimitRange` 로 namespace-별 최소/최대 제한 |
| **Dashboard** | Prometheus + Grafana 로 실시간 자원 사용량·스케일링 히스토리 시각화 |

#### 구현 팁
* `ClusterQueue.spec.cohort` 에 `borrowWithinCohort: true` 로 설정하면 **동일 cohort** 내 풀 간 자동 대여가 가능.  
* `KEDA` 트리거에 **Custom Metrics Adapter** 를 사용해 `Kueue` 가 제공하는 `workload_queue_length` 를 직접 모니터링한다.  

---

## 3️⃣ recoblog 프로젝트 탐색  

### 핵심 개념
* **Just the Docs** 테마 - Jekyll 기반 문서 사이트에 **사이드바, 검색, 버전 관리** 등을 기본 제공.  
* **디렉터리 구조**  
  ```
  recoblog/
  ├─ _config.yml          # Jekyll 설정 (theme, plugins)
  ├─ _data/               # 메뉴·버전 파일
  ├─ _posts/              # markdown 포스트 (YYYY-MM-DD-title.md)
  ├─ _layouts/            # custom 레이아웃
  └─ assets/              # 이미지·CSS·JS
  ```  
* **마크다운 파싱** - 최근 `kramdown` → `jekyll-markdown-parser` 로 교체 작업 진행 중 (링크/코드 블록 오류 해결).

### 배운 점
1. **플러그인 관리**: `jekyll-feed`, `jekyll-sitemap` 등 기본 플러그인 외에 **Just the Docs** 전용 플러그인(`jekyll-toc-generator`) 를 활성화해야 목차 자동 생성이 된다.  
2. **테마 커스터마이징**: `_sass/_variables.scss` 에 색상·폰트 변수 오버라이드 → 전체 UI 통일성 확보.  
3. **CI / CD**: GitHub Actions 로 `jekyll build && gh-pages` 배포 파이프라인을 구축하면 PR 머지 시 자동 배포 가능.  

#### 예시 - `_config.yml` 핵심 설정
```yaml
title: "Recoblog"
theme: just-the-docs
remote_theme: pmarsceill/just-the-docs
url: "https://evanhwang.github.io/recoblog"
logo: "/assets/images/logo.png"

# 플러그인
plugins:
  - jekyll-feed
  - jekyll-sitemap
  - jekyll-seo-tag
  - jekyll-toc

# Just the Docs 옵션
aux_links:
  "GitHub":
    - https://github.com/evanhwang/recoblog
```

---

## 📌 오늘의 정리

| 주제 | 핵심 학습 포인트 | 적용 가능 시나리오 |
|------|----------------|-------------------|
| **pd-disaggregation 레포 탐색** | PD 분산 추론 개념, AWS EFA, 읽기-전용 툴 활용 | 연구 레포 구조 파악 → 실험 재현성 확보 |
| **KAP 자동 스케일링 MVP** | KEDA + PriorityClass + ResourceQuota 로 간단한 선착순/우선순위 정책 구현 | GPU Inference 서비스 초기 자동화 |
| **장기 자동 스케일링 + Quota 아키텍처** | 3-Tier(Reserved/Shared/Burst) 모델, Kueue borrow, 메트릭 기반 확장 | 대규모 멀티-테넌트 클러스터 운영 |
| **recoblog** | Just the Docs 테마 설정, 마크다운 파싱 문제 해결, CI/CD 파이프라인 설계 | 개발·운영 문서 자동화 및 배포 |

> **다음 목표**  
> 1. **KEDA ScaledObject** 와 **Kueue** 를 실제 클러스터에 적용해 **Burst Pool** 의 동작을 검증한다.  
> 2. **recoblog** CI / CD 파이프라인을 완성하고, 새로운 포스트 템플릿을 Just the Docs 스타일에 맞게 확장한다.  

--- 

*이 포스트는 오늘(2026-02-06) Claude Code와 함께 진행한 작업을 Jekyll + Just the Docs 테마 형식으로 정리한 것입니다.*