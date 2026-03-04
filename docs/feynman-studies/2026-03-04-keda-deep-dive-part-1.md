---
layout: default
title: "KEDA 딥다이브 #1: 왜 필요한가, 그리고 아키텍처"
parent: 파인만 학습
nav_order: 20260304
date: 2026-03-04
tags: [kubernetes, keda, autoscaling]
---

# KEDA 딥다이브 #1: 왜 필요한가, 그리고 아키텍처

Kubernetes 워크로드를 운영하다 보면 트래픽이 없을 때도 파드가 떠 있는 상황을 마주한다. 메시지 큐에 작업이 밀려도 HPA가 CPU만 보고 있어서 반응이 느린 경우도 있다. **KEDA(Kubernetes Event-Driven Autoscaling)**는 이런 문제를 해결하기 위해 등장했다.

이 시리즈에서는 KEDA를 아키텍처 수준에서 깊이 있게 다룬다.

> **시리즈 로드맵**
> 1. **왜 필요한가, 그리고 아키텍처** ← 이번 글
> 2. ScaledObject와 트리거 메커니즘
> 3. 실전 패턴과 고급 설정

---

## 배경: HPA만으로는 부족하다

Kubernetes에는 이미 **HPA(Horizontal Pod Autoscaler)**가 있다. 파드의 CPU나 메모리 사용률을 보고 레플리카 수를 자동으로 조절하는 기능이다. 식당에 비유하면, 요리사의 체력(CPU)과 작업대 공간(Memory)을 보고 인력을 늘리거나 줄이는 셈이다.

문제는 HPA가 볼 수 있는 게 제한적이라는 것이다.

### HPA의 한계

**1. 제한된 메트릭**

HPA는 기본적으로 CPU와 Memory만 본다. Prometheus Adapter를 붙이면 커스텀 메트릭도 쓸 수 있지만, 설정이 복잡하다.

```yaml
# Prometheus Adapter 설정 예시 — 큐 길이를 HPA에 노출하려면 이런 규칙이 필요하다
rules:
  - seriesQuery: 'queue_length{namespace!="",pod!=""}'
    resources:
      overrides:
        namespace: { resource: namespace }
        pod: { resource: pod }
    name:
      matches: "^(.*)$"
      as: "${1}"
    metricsQuery: 'sum(<<.Series>>{<<.LabelMatchers>>}) by (<<.GroupBy>>)'
```

요리사의 체력만 보는 게 아니라 키오스크에 쌓인 주문 수를 보고 인력을 결정하고 싶은데, 그러려면 주문 데이터를 Prometheus에 넣고, Adapter에서 변환 규칙을 작성하고, 그걸 다시 HPA에 연결해야 한다. 운영 복잡도가 급격히 올라간다.

**2. Scale-to-Zero 불가**

HPA의 최소 레플리카는 1이다. 트래픽이 전혀 없어도 파드 하나는 항상 떠 있어야 한다. 새벽 3시에 아무도 안 오는 식당에 요리사 한 명이 계속 출근하는 셈이다.

이벤트 기반 워크로드(큐 컨슈머, 배치 프로세서 등)에서는 일이 없을 때 0으로 줄이는 게 비용 효율적이지만, HPA로는 불가능하다.

**3. 느린 반응 속도**

HPA의 컨트롤러 루프는 기본 15초 간격으로 메트릭을 수집한다. Prometheus Adapter를 쓰면 Prometheus의 scrape interval까지 더해져서, 이벤트 발생부터 스케일링 결정까지 수십 초가 걸릴 수 있다.

---

## KEDA가 해결하는 것

KEDA는 HPA를 **대체하는 게 아니라 확장**한다. 핵심 가치는 세 가지다.

| | HPA 단독 | KEDA |
|---|---|---|
| **메트릭 소스** | CPU, Memory (+ Prometheus Adapter) | 60개 이상의 네이티브 스케일러 |
| **Scale-to-Zero** | 불가 (최소 1) | 가능 (0↔1 직접 처리) |
| **운영 복잡도** | Adapter 설정, PromQL 작성 필요 | ScaledObject 하나로 끝 |

### "Event-Driven"이 뜻하는 것

이름에 "Event-Driven"이 들어있지만, KEDA가 순수 push 방식으로 동작하는 건 아니다. 내부적으로는 `pollingInterval`(기본 30초)마다 외부 소스를 확인하는 **폴링** 방식이다.

그러면 왜 "Event-Driven"인가? 이건 전달 **메커니즘**이 아니라 스케일링의 **기준**을 뜻한다.

- **HPA**: 파드 내부 리소스(CPU, Memory) → **리소스 기반** 스케일링
- **KEDA**: 외부 이벤트 소스(메시지 큐 깊이, 스트림 lag, DB 쿼리 결과 등) → **이벤트 소스 기반** 스케일링

Kafka 토픽에 쌓인 메시지, SQS 큐의 대기열, Redis 스트림의 lag — 이런 **외부 이벤트 소스**를 직접 스케일링 기준으로 삼는다는 의미에서 "Event-Driven"이다.

---

## 아키텍처: 네 가지 핵심 컴포넌트

![KEDA Architecture](/assets/images/feynman/2026-03-04-keda-architecture.png)

> [Excalidraw에서 보기](https://excalidraw.com/#json=oRFxZF7mG569xFq5eE5fK,HYwZLfiHRTc6z4HfGeXShw)

### 1. Scaler — 외부 소스를 읽어오는 매니저

Scaler는 외부 이벤트 소스에 **연결해서 현재 메트릭을 읽어오는** 컴포넌트다. 이벤트 소스 자체가 아니라, 이벤트 소스를 확인하러 가는 역할이다. 식당으로 치면 키오스크가 아니라 **키오스크를 확인하러 가는 매니저**에 해당한다.

두 가지 종류가 있다:

- **Built-in Scaler**: KEDA 프로세스 내에서 실행. Kafka, RabbitMQ, AWS SQS, Prometheus 등 60개 이상 지원.
- **External Scaler**: 외부 gRPC 서버로 실행. 커스텀 스케일링 로직이 필요할 때 직접 구현.

### 2. Operator — 0과 1 사이의 결정권자

KEDA Operator는 클러스터의 ScaledObject를 감시하며 두 가지 핵심 역할을 한다.

**첫째, Activation 판단 (0↔1)**

Scaler가 읽어온 메트릭이 `activationThreshold`를 초과하면 파드를 0에서 1로 올린다. 반대로 모든 트리거가 비활성 상태이고 `cooldownPeriod`(기본 300초)가 지나면 0으로 내린다. 이 판단은 HPA 없이 Operator가 직접 한다.

**둘째, HPA 자동 관리**

ScaledObject가 생성되면 Operator는 대응하는 HPA 객체를 자동으로 생성하고 관리한다. 사용자가 HPA를 직접 만들 필요가 없다.

### 3. Metrics Server — HPA에게 외부 메트릭을 전달하는 통역사

KEDA Metrics Server(Metrics Adapter)는 `external.metrics.k8s.io` API로 등록되어, Scaler가 수집한 외부 메트릭을 Kubernetes API Server에 노출한다. HPA는 이 API를 통해 외부 메트릭을 읽고 1↔N 스케일링을 결정한다.

> 주의: 클러스터당 `external.metrics.k8s.io`를 서빙하는 서버는 하나만 가능하다. KEDA를 쓰면 다른 외부 메트릭 서버는 사용할 수 없다.

### 4. CRD — 스케일링 규칙을 선언하는 명세서

| CRD | 역할 |
|---|---|
| **ScaledObject** | Deployment/StatefulSet의 스케일링 규칙 정의. 어떤 이벤트 소스를, 어떤 임계값으로, 몇 개까지 스케일할지 명세. |
| **ScaledJob** | Job 기반 워크로드의 스케일링 규칙 정의. 큐의 메시지마다 Job을 생성하는 패턴에 사용. |
| **TriggerAuthentication** | 외부 이벤트 소스 접근에 필요한 인증 정보(시크릿, 환경변수 등)를 관리. |

---

## 스케일링 흐름: 전체 그림

전체 흐름을 단계별로 정리하면 이렇다.

```
External Event Source (Kafka, SQS, ...)
    │
    ▼
Scaler가 폴링하여 현재 메트릭 확인
    │
    ▼
Operator가 ScaledObject 스펙 기반으로 판단
    │
    ├─ 레플리카 0인데 메트릭 > activationThreshold
    │  → Operator가 직접 0 → 1 스케일링 (Activation)
    │
    └─ 레플리카 1 이상
       → Metrics Server가 외부 메트릭을 API Server에 노출
       → HPA가 메트릭 기반으로 1 ↔ N 스케일링
```

식당 비유로 요약하면:

- **Scaler** = 키오스크를 확인하러 가는 매니저
- **Operator** = 인력 규칙표(ScaledObject)를 보고 채용/해고를 결정하는 점장
- **Metrics Server** = 주문 현황을 인사팀(HPA)에 전달하는 통역사
- **HPA** = 전달받은 현황으로 증원/감원하는 인사팀 (단, 0명 해고는 못 함)

핵심 포인트는 **KEDA가 HPA를 대체하지 않는다**는 것이다. 0↔1 구간만 직접 처리하고, 1↔N 구간은 Kubernetes의 검증된 HPA에 위임한다. KEDA는 HPA가 못하는 빈틈을 채우는 역할이다.

---

## 마무리

KEDA는 결국 "**외부 이벤트 소스를 기준으로, 0까지 포함해서 자동 스케일링하자**"는 단순한 아이디어다. HPA의 한계(제한된 메트릭, scale-to-zero 불가, 운영 복잡도)를 네이티브 스케일러와 Operator 패턴으로 해결한다.

다음 편에서는 ScaledObject의 상세 스펙과 트리거 메커니즘, 그리고 `activationThreshold`와 `threshold`의 차이 등 실전에서 꼭 알아야 할 내용을 다룬다.

---

*이 글은 파인만 학습법을 활용하여 깊이 있게 학습한 내용을 정리한 것입니다.*
