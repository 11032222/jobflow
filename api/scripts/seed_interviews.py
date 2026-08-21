"""面试模块演示数据填充。

与 seed.py 的区别：**本脚本不删除任何数据**，只给已存在的面试补充问题记录、
推进状态并生成复盘。已经有自己岗位/投递数据的同学可以放心单独运行：

    python scripts/seed_interviews.py

seed.py 也会在最后调用本模块，保证一键重置后的演示状态是完整的。

本模块提供 3 组问题集，按顺序填给前 3 场面试：
  第 1 场 已复盘（问题 + 能力画像 + 状态时间线齐全）
  第 2 场 进行中（有问题、尚未复盘）
  第 3 场 已复盘（与第 1 场形成"进步/退步"趋势对比）

若库中面试多于 3 场，多出的保持原样不动（页面上即"已安排、无问题"的空状态）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.interview import Interview, InterviewQuestion  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import interview_review_service, interview_service  # noqa: E402

# 三场面试的问题集。刻意设计成 Redis 由弱转强、MySQL 由强转弱，
# 让知识库的趋势对比（文档 4.x「与历史面试对比→判断进步情况」）有东西可展示。
INTERVIEW_QUESTIONS: list[list[tuple[str, str, str]]] = [
    [
        ("HashMap 的底层实现和扩容机制？",
         "数组+链表+红黑树，负载因子 0.75，链表长度 8 转红黑树", "MASTERED"),
        ("ConcurrentHashMap 1.8 怎么保证线程安全？",
         "CAS + synchronized 锁桶头节点", "MASTERED"),
        ("JVM 垃圾回收算法有哪些？",
         "只说了标记清除和复制算法，没答出分代收集细节", "PARTIAL"),
        ("Redis 的持久化机制有哪些？",
         "只答出 RDB 和 AOF 的基本概念，重写机制没答上", "PARTIAL"),
        ("Redis 缓存穿透怎么解决？", "不会", "FAILED"),
        ("MySQL 索引为什么用 B+树？",
         "磁盘 IO 次数少、叶子节点链表支持范围查询", "MASTERED"),
        ("讲一下你项目中最大的难点", "讲得比较散，没有突出技术决策", "PARTIAL"),
    ],
    [
        ("倒排索引的原理是什么？", "词项到文档的映射，还答了 TF-IDF", "MASTERED"),
        ("Spring 事务失效的场景有哪些？",
         "说了 this 调用和非 public，其他没想起来", "PARTIAL"),
    ],
    [
        ("Redis 分布式锁怎么实现？锁续期怎么做？",
         "SETNX + 过期时间，Redisson 看门狗续期", "MASTERED"),
        ("Redis 缓存雪崩和击穿的区别及解决方案？",
         "雪崩是大面积过期，击穿是热点 key，答出了过期时间打散和互斥重建", "MASTERED"),
        ("MySQL 的 MVCC 是怎么实现的？",
         "只说了快照读，undo log 版本链没答清楚", "PARTIAL"),
        ("MySQL 分库分表后怎么做分页查询？", "不会", "FAILED"),
        ("TCP 三次握手为什么不是两次？",
         "答出了防止历史连接，但序列号同步没说全", "PARTIAL"),
        ("Spring IOC 容器的 Bean 生命周期？",
         "实例化-属性填充-初始化-销毁，答得比较完整", "MASTERED"),
    ],
]

# 每场面试推进到哪个状态：COMPLETED 会自动产出复盘，IN_PROGRESS 保留未复盘态
TARGET_STATUS = ["COMPLETED", "IN_PROGRESS", "COMPLETED"]


def seed_interview_demo(db, user: User) -> int:
    """给用户已有的面试补充演示数据。返回填充的面试场次。

    幂等：已经录过问题的面试直接跳过，重复运行不会产生重复数据。
    """
    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == user.id)
        # 优先填关联了岗位的面试（页面上能显示公司/职位，演示效果好），
        # 未关联岗位的排在后面，通常会被留作"空态"展示
        .order_by(
            Interview.job_id.is_(None),
            Interview.scheduled_at.is_(None),
            Interview.scheduled_at.asc(),
        )
        .all()
    )
    if not interviews:
        print("  未找到面试记录，请先运行 seed.py 或在页面上添加面试")
        return 0

    filled = 0
    for idx, questions in enumerate(INTERVIEW_QUESTIONS):
        if idx >= len(interviews):
            break
        interview = interviews[idx]
        exists = (
            db.query(InterviewQuestion)
            .filter(InterviewQuestion.interview_id == interview.id)
            .first()
        )
        if exists:
            print(f"  面试 {interview.id} 已有问题记录，跳过")
            continue

        for order, (question, answer, mastery) in enumerate(questions):
            db.add(
                InterviewQuestion(
                    interview_id=interview.id,
                    user_id=user.id,
                    question=question,
                    my_answer=answer,
                    mastery=mastery,
                    source="USER",
                    sort_order=order,
                )
            )
        db.commit()

        target = TARGET_STATUS[idx]
        if interview.status == "SCHEDULED":
            interview_service.transition(
                db, interview, "IN_PROGRESS", operator="USER", comment="面试开始"
            )
        if target == "COMPLETED" and interview.status == "IN_PROGRESS":
            interview_service.transition(
                db, interview, "COMPLETED", operator="USER", comment="面试结束"
            )
            review = interview_review_service.start_review(db, interview)
            db.commit()
            # 演示脚本里同步跑完，避免脚本退出时后台任务还没执行
            interview_review_service.run_interview_review(review.id)

        # 复盘在独立会话里提交，MySQL 默认 REPEATABLE READ 下本会话的旧快照读不到，
        # 先 commit 结束当前事务再刷新，否则打印出来的状态是陈旧的
        db.commit()
        db.refresh(interview)
        print(f"  面试 {interview.id}: {len(questions)} 题 -> {interview.status}")
        filled += 1
    return filled


def main() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).order_by(User.id.asc()).first()
        if user is None:
            print("未找到用户，请先运行 scripts/seed.py")
            return
        print(f"=== 填充面试演示数据（用户 {user.username}）===")
        print("本脚本不会删除任何已有数据")
        count = seed_interview_demo(db, user)
        print(f"=== 完成，共填充 {count} 场面试 ===")
        print("  打开「面试管理」页可见能力画像与复盘结果")
    finally:
        db.close()


if __name__ == "__main__":
    main()
