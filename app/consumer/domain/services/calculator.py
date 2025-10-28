"""Consumer Metrics Calculator Service

cal.md 계산 공식 구현
- Fairness Index (Gini Coefficient)
- Rebalance Score
- Delivery Risk ETA
- Policy Advice

참고: cal.md - 전체 계산 공식
"""

from datetime import datetime, timedelta

from app.consumer.domain.models import (
    ConsumerMember,
    ConsumerPartition,
    MemberStats,
    RebalanceRollup,
)
from app.consumer.domain.models.metrics import ConsumerGroupAdvice, FairnessIndex
from app.consumer.domain.types_enum import FairnessLevel, PartitionAssignor


class ConsumerMetricsCalculator:
    """Consumer Group 메트릭 계산 서비스

    cal.md의 계산 공식을 구현

    사용 예시:
    ```python
    calculator = ConsumerMetricsCalculator()

    # Fairness Index 계산
    fairness = calculator.calculate_fairness(members, partitions)

    # Policy Advice 생성
    advice = calculator.generate_advice(group, members, rollup)
    ```
    """

    def calculate_fairness(
        self, members: list[ConsumerMember], partitions: list[ConsumerPartition]
    ) -> FairnessIndex:
        """Fairness Index 계산 (cal.md 4️⃣)

        계산 공식:
        G = Σ_i Σ_j |x_i - x_j| / (2 * n^2 * mean(x))

        Args:
            members: Consumer Member 목록
            partitions: Consumer Partition 목록

        Returns:
            FairnessIndex (Gini Coefficient 포함)
        """
        if not members:
            return FairnessIndex(
                gini_coefficient=0.0,
                member_count=0,
                avg_tp_per_member=0.0,
                max_tp_per_member=0,
                min_tp_per_member=0,
            )

        # 멤버별 파티션 수
        tp_counts = [m.assigned_tp_count for m in members]
        n = len(tp_counts)

        if n == 0:
            return FairnessIndex(
                gini_coefficient=0.0,
                member_count=0,
                avg_tp_per_member=0.0,
                max_tp_per_member=0,
                min_tp_per_member=0,
            )

        # 기본 통계
        total_tp = sum(tp_counts)
        mean_tp = total_tp / n if n > 0 else 0.0
        max_tp = max(tp_counts) if tp_counts else 0
        min_tp = min(tp_counts) if tp_counts else 0

        # Gini Coefficient 계산
        if mean_tp == 0:
            gini = 0.0
        else:
            # Σ_i Σ_j |x_i - x_j|
            sum_abs_diff = sum(abs(xi - xj) for xi in tp_counts for xj in tp_counts)
            gini = sum_abs_diff / (2 * n * n * mean_tp)

        return FairnessIndex(
            gini_coefficient=gini,
            member_count=n,
            avg_tp_per_member=mean_tp,
            max_tp_per_member=max_tp,
            min_tp_per_member=min_tp,
        )

    def calculate_member_stats(
        self, member: ConsumerMember, partitions: list[ConsumerPartition]
    ) -> MemberStats:
        """멤버별 통계 계산

        Args:
            member: Consumer Member
            partitions: 해당 멤버가 담당하는 파티션 목록

        Returns:
            MemberStats (total_lag, avg_lag 포함)
        """
        member_partitions = [p for p in partitions if p.assigned_member_id == member.member_id]

        lags = [p.lag for p in member_partitions if p.lag is not None]
        total_lag = sum(lags) if lags else 0
        avg_lag = total_lag / len(lags) if lags else 0.0

        return MemberStats(
            member_id=member.member_id,
            assigned_tp_count=member.assigned_tp_count,
            total_lag=total_lag,
            avg_lag=avg_lag,
        )

    def calculate_delivery_risk_eta(
        self,
        current_lag: int,
        previous_lag: int | None,
        delta_seconds: float,
        target_lag: int,
    ) -> datetime | None:
        """배달 위험 ETA 계산 (cal.md 6️⃣)

        계산 공식:
        - lag_slope = (lag_t - lag_(t-1)) / Δt
        - ETA = current_ts + (target_lag - current_lag) / lag_slope

        Args:
            current_lag: 현재 lag
            previous_lag: 이전 lag (None이면 계산 불가)
            delta_seconds: 시간 간격 (초)
            target_lag: 목표 lag (임계값)

        Returns:
            ETA datetime (위반 예상 시각) or None (계산 불가 또는 안전)
        """
        # 1. 이전 데이터 없으면 계산 불가
        if previous_lag is None or delta_seconds <= 0:
            return None

        # 2. 이미 목표 초과 중이면 즉시 반환
        if current_lag >= target_lag:
            return datetime.now()

        # 3. Lag 증가 속도 계산
        lag_slope = (current_lag - previous_lag) / delta_seconds

        # 4. Lag이 감소 중이거나 변화 없으면 안전
        if lag_slope <= 0:
            return None

        # 5. ETA 계산
        remaining_lag = target_lag - current_lag
        eta_seconds = remaining_lag / lag_slope

        # 6. 현재 시각 + ETA
        eta = datetime.now() + timedelta(seconds=eta_seconds)

        return eta

    def generate_advice(
        self,
        current_assignor: PartitionAssignor | None,
        rebalance_rollup: RebalanceRollup | None,
        fairness: FairnessIndex,
        total_partitions: int,
        member_count: int,
        p95_lag: int,
        target_p95_ms: int = 10000,
        previous_p95_lag: int | None = None,
        delta_seconds: float | None = None,
    ) -> ConsumerGroupAdvice:
        """정책 권고 생성 (cal.md 7️⃣)

        권고 항목:
        - Assignor 추천 (cooperative-sticky 권장)
        - Static Membership 추천
        - Scale-out 추천 (consumer 추가 or partition 추가)
        - Delivery Risk ETA (위반 예상 시각)

        Args:
            current_assignor: 현재 Assignor
            rebalance_rollup: 리밸런스 롤업 통계
            fairness: Fairness Index
            total_partitions: 전체 파티션 수
            member_count: 멤버 수
            p95_lag: 현재 P95 Lag
            target_p95_ms: 목표 P95 Lag (기본 10000ms)
            previous_p95_lag: 이전 P95 Lag (ETA 계산용, Optional)
            delta_seconds: 시간 간격 (ETA 계산용, Optional)

        Returns:
            ConsumerGroupAdvice (risk_eta 포함)
        """
        # 1. Assignor 권고
        assignor_recommendation = None
        assignor_reason = None
        if current_assignor != PartitionAssignor.COOPERATIVE_STICKY:
            assignor_recommendation = "cooperative-sticky"
            assignor_reason = "Incremental rebalancing으로 처리 중단 최소화"

        # 2. Static Membership 권고
        static_membership_recommended = False
        static_membership_reason = None
        if rebalance_rollup and rebalance_rollup.rebalance_score() < 70:
            static_membership_recommended = True
            static_membership_reason = (
                f"잦은 리밸런스 발생 (점수: {rebalance_rollup.rebalance_score():.1f})"
            )

        # 3. Scale 권고
        scale_recommendation = None
        scale_reason = None

        # Lag 초과 시 consumer 추가 권장
        if p95_lag > target_p95_ms * 2:
            scale_recommendation = "increase_consumers"
            scale_reason = f"P95 lag 과다 ({p95_lag}ms > 목표 {target_p95_ms}ms의 2배)"

        # Fairness 불균형 시 partition 추가 권장
        elif fairness.level() == FairnessLevel.HOTSPOT:
            if member_count > 0 and total_partitions / member_count < 2:
                scale_recommendation = "add_partitions"
                scale_reason = f"파티션 부족으로 불균형 (Gini: {fairness.gini_coefficient:.2f})"

        # 4. SLO 준수율 계산
        slo_compliance_rate = 1.0 if p95_lag <= target_p95_ms else 0.0

        # 5. Delivery Risk ETA 계산 (cal.md 6️⃣)
        risk_eta = None
        if previous_p95_lag is not None and delta_seconds is not None:
            risk_eta = self.calculate_delivery_risk_eta(
                current_lag=p95_lag,
                previous_lag=previous_p95_lag,
                delta_seconds=delta_seconds,
                target_lag=target_p95_ms,
            )

        return ConsumerGroupAdvice(
            assignor_recommendation=assignor_recommendation,
            assignor_reason=assignor_reason,
            static_membership_recommended=static_membership_recommended,
            static_membership_reason=static_membership_reason,
            scale_recommendation=scale_recommendation,
            scale_reason=scale_reason,
            slo_compliance_rate=slo_compliance_rate,
            risk_eta=risk_eta,
        )
