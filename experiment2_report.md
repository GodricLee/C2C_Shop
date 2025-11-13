# 实验二：软件设计与建模（网络商场系统）
> 学号：___231502004___　姓名：___李子___　日期：2025-10-31  

---

## 0. 摘要
C2C 类“咸鱼”网络商场，核心约束：**强制 2FA + 风控**；**无在线支付**（联系方式交换视为成交）；**卖家确认成交触发返现**；**优惠券双下限（目标收益/目标销量）**；**会员价叠加受最低价/补贴上限**；**唯一管理员 + 审计留痕 + 参数版本化**。  
配套 UML：**类图、用例图、活动图、时序图、组件图**；UI 原型覆盖登录与 2FA、搜索、商品详情与联系交换、卖家成交确认、管理员规则、会员中心。

---

## 1. 主要功能
- **账户与安全**：注册/登录/退出、2FA（邮箱/短信/TOTP）、设备指纹、异常登录风控、会话管理与审计。
- **商品与搜索**：发布/编辑/下架/浏览；模糊/同义词搜索；标签（卖家自定义→后台审核→合并/批量导入）。
- **促销与会员**：卖家确认成交触发返现；优惠券双下限校验；会员价与额外券叠加并受最低价、补贴上限。
- **后台与审计**：唯一管理员；抽成/返现/优惠/会员规则；参数版本化与回滚；全量操作日志。
- **UI 与集成**：响应式 UI；联系方式交换闭环；**PaymentAdapter** 预留未来支付接入。

---

## 2. 架构总览
**文件**：`UML/UML组件图.puml`（导出：`UML/UML组件图.png`）  



**要点**：客户端（Web 前端 SPA、移动端 H5）→ **API 网关** → 微服务：`AccountService / ProductService / SearchService / PromotionService / MembershipService / AdminService / AuditService / RiskService / NotificationService`；  
数据层：`UserDB / ProductDB / PromoDB / AuditDB / SearchIndex`；外部：`SMTP / SMS / 支付(预留)`；促销/后台写入 **Audit**；支付通过 **PaymentAdapter** 适配。

---

## 3. UML 图与设计说明

### 3.1 类图（必选）
**文件**：`UML/UML类图.puml`（导出：`UML/UML类图.png`）  

<img src="C:\Users\李子\AppData\Roaming\Typora\typora-user-images\image-20251031225804463.png" alt="image-20251031225804463" style="zoom: 400%;" />

**分包**：

- **Account & Security**：`User`（`roles: Set<Role>`，`twoFAEnabled`）`Session`、`TwoFAMethod(type: EMAIL/SMS/TOTP)`、`DeviceFingerprint`、`RiskEvent(type: ABNORMAL_LOGIN/MULTI_DEVICE/SUSPICIOUS_LOCATION)`、`Role/ UserStatus`。  
  关系：`User 1 o-- * Session / TwoFAMethod / DeviceFingerprint / RiskEvent`。
- **Product & Search**：`Product(status: DRAFT/PUBLISHED/UNLISTED/SOLD)`、`Tag(status: PENDING/APPROVED/REJECTED/MERGED)`、`TagAudit`、`SearchService`、`SynonymEntry`。  
  关系：`Product * -- * Tag`；`Tag 1 o-- * TagAudit`；`SearchService ..> SynonymEntry`；`Product 1 --> 0..* SynonymEntry`。
- **Promotion & Membership**：`Membership(level: NORMAL/SHOPPER)`、`Coupon(status: DRAFT/ACTIVE/EXPIRED/DISABLED, minRevenue, minSales, discount)`、`CouponAssignment`、`Cashback(ratio, amount)`、`PricePolicy(minPrice, subsidyCap)`、`DiscountEngine(calcEffectivePrice, validatePolicy)`。  
  关系：`User 1 -- 0..* CouponAssignment`；`CouponAssignment * -- 1 Coupon`；`Coupon * -- 0..* Product`。
- **Admin & Audit**：`AdminConfig(commissionRate, cashbackDefault)`、`ParameterSet(version, effectiveAt)`、`AuditLog(actor, action, diff)`；`AdminConfig 1 o-- * ParameterSet`；`AuditLog * --> 1 User: actor`。
- **UI & Integration**：`ContactExchangeRecord`、`Deal(status: INITIATED/CONFIRMED_BY_SELLER/CANCELED)`、`PaymentAdapter<<interface>>`。  
  关系：`Deal * -- 1 Product / 1 User(buyer) / 1 User(seller)`；`Deal * --> 0..1 Cashback : triggers`；`Deal ..> PaymentAdapter : future`；`ContactExchangeRecord` 连接 `买家/卖家/Product`。

**设计理由**：安全与交易域分离；促销域聚合 `Coupon/Member/PricePolicy/DiscountEngine`；运营可控（`AdminConfig + ParameterSet + AuditLog`）；未来支付可插拔（`PaymentAdapter`）。

---

### 3.2 用例图（行为性）

![image-20251031225858664](C:\Users\李子\AppData\Roaming\Typora\typora-user-images\image-20251031225858664.png)

**文件**：`UML/UML用例图.puml`（导出：`UML/UML用例图.png`）  
**参与者**：买家、卖家、管理员。  
**用例**：`注册`、`登录[2FA]`、`查看/搜索商品`、`发布/编辑/下架商品`、`交换联系方式`、`确认成交`、`查看/管理返现记录`、`领取/使用优惠券`、`升级会员与管理会员权益`、`后台配置抽成/返现/优惠/会员规则`、`标签审核与合并`、`查看审计日志`、`风险评估与额外验证`、`生成返现记录`。  
**包含/扩展**：`登录 ->(include)-> 风险评估与额外验证`；`确认成交 ->(include)-> 生成返现记录`；`优惠券 ->(extend)-> 确认成交`。

---

### 3.3 活动图（行为性）——成交确认触发返现

![image-20251031225915986](C:\Users\李子\AppData\Roaming\Typora\typora-user-images\image-20251031225915986.png)

**文件**：`UML/UML活动图_返现与交易确认.puml`（导出：`UML/UML活动图_返现与交易确认.png`）  
**主干**：买家浏览→交换联系方式（系统记录）→ 卖家后台**确认成交** →  
分支 **是否使用优惠券？** → 若是：**校验目标收益/目标销量**，失败**直接阻止**；通过→计算成交价 → 计算返现 → 生成返现记录 → 写审计 → 通知双方。未用券：跳过校验。

---

### 3.4 时序图（交互性）——登录 + 2FA + 风控

![image-20251031225936535](C:\Users\李子\AppData\Roaming\Typora\typora-user-images\image-20251031225936535.png)

**文件**：`UML/UML序列图_登录2FA.puml`（导出：`UML/UML序列图_登录2FA.png`）  
**参与者**：`用户 U / WebApp UI / AuthController / AccountService / RiskEngine / TwoFAService / SessionService / AuditLog(DB)`  
**流程**：密码校验→风险评分→根据策略**强制 2FA（Email/SMS/TOTP）**→验证通过则创建会话并审计；失败则拒绝并留痕。

---

## 4. UI 界面与功能说明（SALT 原型）

1) **登录与二次验证**（`UI界面/登录与2FA.puml` → `登录与2FA.png`）  

![image-20251031225953302](C:\Users\李子\AppData\Roaming\Typora\typora-user-images\image-20251031225953302.png)

   - 账号/密码登录，**异常登录强制触发 2FA**；支持邮箱/短信/TOTP；验证码发送与校验；忘记密码、自动登录选项。

2) **搜索与筛选**（`UI界面/搜索与筛选.puml` → `搜索与筛选.png`）  

![image-20251031230004580](C:\Users\李子\AppData\Roaming\Typora\typora-user-images\image-20251031230004580.png)

   - 关键词；分类/标签/价格区间；排序（综合/价格升降/最新）；分页列表与空态提示。

3) **商品详情与联系方式交换**（`UI界面/商品详情与联系交换.puml` → `商品详情与联系交换.png`）  

![image-20251031230011698](C:\Users\李子\AppData\Roaming\Typora\typora-user-images\image-20251031230011698.png)

   - 展示标题/价格/状态/标签；**联系卖家**弹窗（微信/手机/邮箱）；生成联系交换记录；收藏/举报。

4) **卖家后台 · 成交确认**（`UI界面/卖家后台_成交确认.puml` → `卖家后台_成交确认.png`）  

![image-20251031230016752](C:\Users\李子\AppData\Roaming\Typora\typora-user-images\image-20251031230016752.png)

   - 待确认列表（商品/买家/联系方式/状态）；选择优惠券并**校验阈值**；未通过**禁止确认**。

5) **管理员后台 · 规则与审计**（`UI界面/管理员后台_规则配置.puml` → `管理员后台_规则配置.png`）  

![image-20251031230026269](C:\Users\李子\AppData\Roaming\Typora\typora-user-images\image-20251031230026269.png)

   - 抽成比例、默认返现比例、**最低售价/补贴上限**；参数**版本选择/保存草稿/发布/回滚**；最近审计日志。

6) **会员中心与优惠券**（`UI界面/会员中心与优惠券.puml` → `会员中心与优惠券.png`）  

![image-20251031230033220](C:\Users\李子\AppData\Roaming\Typora\typora-user-images\image-20251031230033220.png)

   - 等级（普通/购物会员）、到期时间、升级/续费；权益说明；我的优惠券（可用/已用）与“使用”。

---

## 5. 关键业务规则
- **2FA & 风控**：所有登录强制 2FA；高风险追加验证（设备指纹、IP/地理异常）；全部审计。  
- **成交与返现**：**卖家确认**即成交；按比例生成 `Cashback` 记录并留痕。  
- **优惠券双下限**：`minRevenue` 与 `minSales` 任一不达标 → 报错并阻止。  
- **会员价叠加**：叠加后受 `PricePolicy(minPrice, subsidyCap)` 约束。  
- **标签与同义词**：卖家自定义标签需审核；支持合并/下线；搜索用 `SynonymEntry` 提升召回。  
- **唯一管理员**：关键配置（抽成/返现/优惠/会员价）均审计，参数**版本化可回滚**。

---

## 6. 数据与索引（对应类图）
核心实体/表：`User / TwoFAMethod / Session / DeviceFingerprint / RiskEvent / Product / Tag / TagAudit / SynonymEntry / Coupon / CouponAssignment / Membership / Deal / Cashback / AdminConfig / ParameterSet / AuditLog`；  
索引：`SearchIndex`（标题/描述分词 + 同义词扩展）；过滤维度：标签/价格/状态。

## 7.大模型使用记录

### 1. 主要使用场景

我一开始让模型帮我画出几种 UML 图的雏形，包括类图、用例图、活动图和时序图。它能很快搭出框架，比如把用户、商品、返现、优惠券这些对象之间的关系整理出来。但我发现它在写类图的时候 PlantUML 的语法细节一直他妈的出错渲染失败，比如用尖括号就会报错，恶心了我很久时间，于是我只能让大模型来重复查错，加上我自己手动瞪眼观察法，好不容易改成波浪线写法，还把枚举改成 <>才渲染成功。顺便补上返现逻辑和价格政策的部分。活动图那块，我让模型先生成主线流程，再自己加上失败分支，比如“优惠券阈值不通过直接终止”。

时序图的帮助也挺大，它帮我快速确定了登录、风控、2FA、审计的参与者和消息顺序；我只补了异常路径和日志细节。组件图和 UI 原型也类似，模型先给我一个框架，我再改成符合自己逻辑的样子。UI 那几张图我重点改了交互，比如校验失败禁止成交、参数回滚、空态提示这些细节。

### 2. 整体体验与反思

说实话，大模型最大的作用是**加速起步**。以前要想清结构、再去画，得几个小时；现在十分钟就能出初稿，我只要动脑优化就行。它对结构性的东西（比如模块拆分、流程顺序）非常快，但对项目里那些“为什么要这样做”的策略逻辑——比如双下限、风控触发条件、管理员唯一登录——理解就比较浅，只能靠我自己补。

生成的内容大体正确，但语气太机械，格式死板，所以我基本都重写成自己的表达，让报告更自然。

## 8. 总结

我觉得，大模型在软件设计阶段最适合做“草图师”和“陪练”，而不是“决策者”。最好的用法是：

- **先自己定清边界**，再让它画结构。别让它带着你跑，而是用它来验证思路。
- **多轮对比生成**，选出结构最合理的一版，融合到自己的版本中。
- **把规则显性化**，像“阈值不通过即终止”“所有登录都审计”这种约束，必须写在模型里，而不是放在脑子里。
- **关注可维护性**，用接口和适配器（例如 PaymentAdapter）预留扩展空间。

总的来说，它帮我节省了大量画图和排版时间，也让我在修改中更快发现逻辑漏洞。但真正决定系统好坏的，依然是人的判断和细节思维。大模型能提供一张地图，但路线怎么走，还得靠自己。