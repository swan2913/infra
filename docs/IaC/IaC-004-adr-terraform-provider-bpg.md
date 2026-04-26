# IaC-004 · ADR — Terraform Proxmox 프로바이더 선택: bpg/proxmox

> 작성일: 2026-04-25  
> 상태: **채택**

## 결정

Terraform으로 Proxmox VE를 관리할 프로바이더로 `bpg/proxmox`를 선택한다.

## 맥락

Proxmox VE용 Terraform 프로바이더는 사실상 두 가지가 존재한다.

| 항목 | `bpg/proxmox` | `telmate/proxmox` |
|------|--------------|-------------------|
| 유지보수 | 활발 (2024년 지속 릴리즈) | 사실상 방치 (2022년 이후 거의 없음) |
| API 방식 | REST API + SSH 병행 | REST API만 |
| 리소스명 | `proxmox_virtual_environment_vm` | `proxmox_vm_qemu` |
| cloud-init | 네이티브 지원, 세밀한 제어 가능 | 제한적 |
| GPU 패스스루 | 지원 | 지원하나 설정 방식 불편 |
| Proxmox 8.x 호환 | ✅ 안정 | 불안정 |
| 문서 | 상세하고 최신 | 오래됨 |

## 선택: `bpg/proxmox ~> 0.78`

## 이유

1. **Proxmox 8.x 호환성**: 현재 환경은 Proxmox VE 8.x(9.x)를 사용한다. `telmate`는 8.x에서 불안정한 동작이 보고되어 있다.
2. **cloud-init 지원**: VM 100/101 모두 Ubuntu cloud image + cloud-init으로 프로비저닝한다. `bpg`는 이를 네이티브로 지원한다.
3. **GPU 패스스루**: VM 101에 RTX 3080 PCIe 패스스루가 필요하다. `bpg`의 `hostpci` 블록이 더 직관적으로 설정된다.
4. **장기 유지보수**: `telmate`는 사실상 방치 상태로, 신규 Proxmox 기능 추가 시 대응을 기대하기 어렵다.

## 포기한 대안

### `telmate/proxmox`
오래된 블로그 예제나 Reddit 가이드에 많이 등장하지만, 2022년 이후 유지보수가 거의 없다. Proxmox 8.x 환경에서 cloud-init, 디스크 resize, GPU 패스스루 설정 시 문제가 보고된다. 향후 Proxmox 버전 업그레이드 시 호환성 문제가 발생할 가능성이 높아 선택하지 않았다.

## 결과

`terraform/proxmox/providers.tf`에 아래와 같이 고정한다.

```hcl
terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.78"
    }
  }
}
```

버전 고정(`~> 0.78`)은 마이너 업데이트는 수용하되 메이저 API 변경은 차단하기 위함이다.
