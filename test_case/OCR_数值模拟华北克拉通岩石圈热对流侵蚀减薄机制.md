<!-- Page 1 -->

中国科学: 地球科学 2013 年 第 43 卷 第 4 期: 642 ~ 652

www.scichina.com earth.scichina.com

《中国科学》杂志社
SCIENCE CHINA PRESS

论文

# 数值模拟华北克拉通岩石圈热对流侵蚀减薄机制

乔彦超 $^{①②③*}$，郭子祺 $^{①③}$，石耀霖 $^{②}$

① 中国科学院遥感应用研究所，北京 100101；

② 中国科学院研究生院地球动力学重点实验室，北京 100039；

③ 遥感科学国家重点实验室，北京 100101

* E-mail: oliver.qiao@gmail.com

收稿日期: 2012-09-12; 接受日期: 2012-12-27

国家自然科学基金(批准号: 90814014, 40971226)、国土资源部深部探测技术与实验研究专项(编号: SinoProbe-07)、国土资源部深部探测技术与实验研究专项(编号: 201011080-02 SinoProbe09-03)和中国科学院知识创新工程重要方向项目(编号: KZCX2YW123)资助

## 摘要
 关于华北克拉通岩石圈减薄机制，国内外学者通过各种研究定性地提出了不同的机制。文章根据最近几年国内外发表的有关资料，通过数值模拟方法，主要对华北克拉通岩石圈热对流侵蚀的减薄机制进行了计算。通过我们的计算证实了原来稳定存在的克拉通，如底边界为 1673 K 时的初始情形，在底部温度扰动升高后，由于浮力驱动的小尺度地幔对流加剧能够使岩石圈发生大规模减薄，减薄速率在 mm/a 的量级，减薄的时间尺度基本都在十几个百万年；计算过程中我们讨论了初始参考等效粘滞系数分别为  $\eta_0 = 1.0 \times 10^{22}$ Pa s 和  $\eta_0 = 1.0 \times 10^{23}$ Pa s 的两种情形，在这两种条件下，我们分别计算了底边界温度为 1773, 1873, 1973 和 2073 K 的 4 种情况。通过不同端员的计算我们知道岩石圈最多从 200 km 减薄到 100 km，至少减薄到 126.25 km，这符合现今地球物理观测的结果。并且初始参考等效粘滞系数和底边界温度是影响减薄速率的重要因素。

关键词

华北克拉通

岩石圈

热对流

减薄机制

克拉通是地球表面上相对稳定的构造单元，它由上部古老的大陆地壳和下部的岩石圈地幔所组成。克拉通岩石圈，特别是其古老岩石圈地幔具有较低的密度，因而能够长久漂浮在地球的表面。而它本身巨大的岩石圈厚度(约200 km)和较低的热流，不易被俯冲破坏，能够使其较少受到其他地质作用的影响而保持其长期的稳定性。这就是克拉通为什么是地球上最稳定的构造单元的原因 $^{[1]}$。

然而，并不是所有的前寒武纪克拉通从它们形成以后都是处于稳定状态。它们中的大多数在自古元古代聚合后一直保持相对稳定，而另一些克拉通在新元古代和显生宙由于克拉通再活化而发生减薄。也正因为如此，克拉通岩石圈的改造和破坏已经成为大陆动力学研究的一个热点。例如，若干证据(地表地质学、捕捞体的研究、地震和热流数据)表明，形成于早前寒武纪的华北克拉通，其厚的岩石圈根部在显生宙发生丢失 $^{[2,3]}$。这样，华北克拉通已经成为世界上研究克拉通活化和再造的典型地区 $^{[4-6]}$。

尽管目前大家公认，岩石圈减薄是中国东部地质演化的基本事实，但对岩石圈减薄的具体时间、机制及其控制因素，仍存在激烈的争论。关于岩石圈的减薄机制 Gao 等 $^{[7,8]}$在燕山地区的研究，获得了下地壳和岩石圈地幔物质进入软流圈地幔的岩石学证据，认为“拆沉作用”是岩石圈减薄的方式。国内外学者 $^{[9-12]}$的

中文引用格式：乔彦超，郭子祺，石耀霖. 数值模拟华北克拉通岩石圈热对流侵蚀减薄机制. 中国科学：地球科学，2013，43：642-652

英文引用格式：Qiao Y C, Guo Z Q, Shi Y L. Thermal convection thinning of the North China Craton: Numerical simulation. Science China: Earth Sciences, 2013, 56: 773-782, doi: 10.1007/s11430-013-4588-3

---

<!-- Page 2 -->

中国科学：地球科学 2013 年 第 43 卷 第 4 期

相关研究，提出了软流圈热物质上涌主导的热侵蚀作用是岩石圈破坏的热侵蚀方式。Zhang $^{[13]}$通过分析玄武岩携带的橄榄石捕房晶和辉石捕房体中的环带结构，提出多来源熔体与橄榄岩相互作用是造成岩石圈地幔性质改变的有效途径。岩石学和地球化学研究，获得了许多来自地球深部样品的直接数据，探讨了可能改变岩石圈地幔性质的物理和化学过程，提出了拆沉作用、热侵蚀作用、橄榄岩-熔体相互作用和机械拉张等有关破坏方式的多种见解 $^{[5,14]}$。但是这些理论同时也非常需要数值模拟能够在时间和空间范围的计算来验证，使这些理论能够被大家直观的接受。

在地球内部除了与板块运动相联系的全球尺度的大规模对流外，还很可能存在小尺度的上地幔对流 $^{[15-17]}$。最近20年来，用数值模拟或实验模拟的方法对小尺度地幔对流进行了大量的研究 $^{[18,19,20-34]}$，研究内容包括小尺度地幔对流的发生、发展与热演化 $^{[21,26,28]}$、重力异常 $^{[19]}$及其波长特征 $^{[19,30]}$等。小尺度地幔对流的发生主要取决于地幔黏性结构 $^{[21,26,28]}$，根据目前对地幔黏性的理解 $^{[35]}$，即使顾及其不确定性，软流圈中极有可能存在小尺度地幔对流，这与地震学的研究结果相一致 $^{[36-39]}$。

高压下矿物的蠕变试验表明 $^{[35]}$，地幔、特别是岩石圈的黏度强烈地依赖于温度和压力。关于变黏度问题的对流研究，自20世纪80年代以来已有相当多的工作 $^{[40-44]}$。由于问题的复杂性，几乎所有的工作都是利用数值方法，包括有限元及有限差分。Christensen等 $^{[40-42]}$就二维及三维的变黏度对流进行了系统的研究，数值模拟结果表明，黏度结构对对流的形态、格局及内部热状态有非常重要的影响。Tackley $^{[43]}$及Zhong和Zuber $^{[44]}$则分别在直角坐标和球坐标下，探讨了黏度随温度变化的本构关系对全球地幔对流的影响。

本篇文章根据最近几年国内外发表的有关资料，通过数值模拟方法，对华北克拉通岩石圈热对流侵蚀的减薄机制进行了计算。讨论它需要的热条件，可能的减薄速率，以及影响减薄过程的多种因素，探索它是否是一种可能的机制。

## 1 数值模型

### 1.1 数值计算的基本原理

上地幔的热对流可以用质量、动量和能量守恒定律描述。因为地幔对流中的普朗特数(Prandtl)为  $10^{24}$ 的量级 ( $Pr = C_p \eta / k$，其中  $C_p$ 是热容量， $\eta$ 是粘滞系数， $k$ 是热导率)，我们做了无限普朗特数假定，即忽略动量方程中的惯性力。同时我们做了 Boussinesq 假定 $^{[45,46]}$，即除了动量定理中浮力项密度会随温度稍微变化外，密度可以假定为常数。并且认为流体不可压缩，由上述物理定律描述的流体动力学基本方程组如下：

不可压缩的连续性方程： $\frac{\partial v_{x}}{\partial x}+\frac{\partial v_{z}}{\partial z}=0.$

(1)

二维流体斯托克斯方程： $\frac{\partial\sigma_{xx}}{\partial x}+\frac{\partial\sigma_{xz}}{\partial z}=\frac{\partial P}{\partial x}.$

(2)

$$ \frac{\partial\sigma_{zz}}{\partial z}+\frac{\partial\sigma_{xz}}{\partial x}=\frac{\partial P}{\partial z}-g_{z}\rho(P,T). $$

(3)

本构方程：

$$ \sigma_{x x}=2\eta\varepsilon_{x x}; $$

(4)

$$ \sigma_{x z}=2\eta\varepsilon_{x z}; $$

(5)

$$ \sigma_{z z}=2\eta\varepsilon_{z z}; $$

(6)

$$ \varepsilon_{x x}=\frac{\partial v_{x}}{\partial x}; $$

(7)

$$ \varepsilon_{x z}=\frac{1}{2}\bigg(\frac{\partial v_{x}}{\partial z}+\frac{\partial v_{z}}{\partial x}\bigg); $$

(8)

$$ \varepsilon_{z z}=\frac{\partial v_{z}}{\partial z}. $$

(9)

能量方程： $\rho C p\left(\frac{DT}{Dt}\right)=\frac{\partial q_{x}}{\partial x}+\frac{\partial q_{z}}{\partial z};$

(10)

$$ q_{x}=-k\left(\frac{\partial T}{\partial x}\right); $$

(11)

$$ q_{z}=-k\left(\frac{\partial T}{\partial z}\right). $$

(12)

其中  $x, z$ 分别代表水平方向和垂直方向坐标； $v_x, v_z$ 分别为速度向量的分量 (m/s)； $t$ 是时间 (s)； $\sigma_{xx}, \sigma_{xz}, \sigma_{zz}$ 分别是粘性偏应力张量的分量 (Pa)； $\varepsilon_{xx}, \varepsilon_{xz}, \varepsilon_{zz}$ 是应变率张量的分量 (s $^{-1}$)； $P$ 是压力 (Pa)； $T$ 是温度 (K)； $q_x, q_z$ 是水平方向和垂直方向的热流量 (W/m)； $\rho$ 是密度 (kg/m $^3$)，与温度相关； $g_z$ 是重力加速度 (m/s $^2$)； $k$ 是热导率 (W/(m K $^{-1}$))； $C_p$ 是热容量 (J/(Kg K $^{-1}$))； $\eta$ 是等效粘滞系数 (Pa s)，尽管在不同的压力、温度及应变率条件下，地幔-岩石圈系统有着不同的变形机制，但其中对粘滞系数具有最主要的影响的因素是温度 $^{[40]}$。本文假定粘滞系数与温度为指数关系，并可以用表达式近似表示为 $^{[47]}$

643

---

<!-- Page 3 -->

乔彦超等：数值模拟华北克拉通岩石圈热对流侵蚀减薄机制

$$ \eta = \eta_ {0} \exp \left(- b \frac {T - T _ {\mathrm{top}}}{T _ {\mathrm{bottom}} - T _ {\mathrm{top}}}\right). \tag {13} $$

密度与温度的线性关系如下式：

$$ \rho = \rho_ {0} [ 1 - \alpha (T - T _ {\mathrm{top}}) ], \tag {14} $$

式中， $T_{top}$  是模型顶部温度(K)； $T_{bottom}$  是模型底部温度(K)； $\eta_{0}$ ， $\rho_{0}$  是模型顶部( $T=T_{top}$ ; z=0)处的粘滞系数和密度；b 是一个常数，它的大小控制着系统内部的粘滞系数差异； $\alpha$  是热膨胀系数(1/K).

#### 1.2 数值模拟方法的验证

数值模拟使用了2D的“I2VIS” $^{[48\sim50]}$ ，基于有限差分法和marker-in-cell(MIC)技术.为了证明数值方法的可靠性，本文基于Blankenbach等 $^{[51]}$ 的benchmark工作(表1)对本程序进行了验证.

表 1 包括 2 种对流模型，其中模型 1a 中粘滞系数不随温度深度变化，模型 2a 中粘滞系数跟温度和深度相关，两种模型中密度都随温度变化。研究的是方盒子热对流，高为 H，宽为 L。边界条件是所有的边都为自由边界条件，顶边界温度为  $T_{top}=273\ K$ ，底边界温度为  $T_{bottom}=1273\ K$ ，左右两个边界是绝热边界条件  $(\partial T/\partial x=0)$ 。b 等参数值见表 1。

虽然这些相对简单的设置，但是要获得地幔对流的精确的稳定解还是很有挑战性的。主要原因有：(1) 要获得稳定解一般需要几千步的计算时间步；(2) 当粘滞系数比较小，即瑞利数 $Ra\left(Ra = \frac{\rho_0\alpha(T_{\text{bottom}} - T_{\text{top}})gH^3C_p}{\eta k}\right)$ 比较大时，在流动剧烈的区域会有局限性；因此我们在计算中要采取合适的时间步长，选取符合实际的粘滞系数。同时需要指出，验证模型时我们计算了1 Ma的时间，我们计算给出的开始时刻都是对应第一个时间步，最后时刻都是对应最后一个时间步。

计算中我们采用 $51 \times 51$ 的网格，40000个示踪点(markers).

如表 2, 图 1 中模型 1a 和模型 2a Nusselt 数与 Vrms 值与 Blankenbach 的 benchmark 值对比图. 通过计算模型 1a 中 Nusselt 数误差为 0.98%, Vrms 值误差为 0.5%; 模型 2a 中努赛特数误差为 0.14%, Vrms 值误差为 1%. 从这个结果来看我们的计算程序计算此问题是可靠的.

#### 1.3 数值计算的条件

所研究的区域为上地幔-岩石圈系统，计算模型为 $700\mathrm{km}\times 700\mathrm{km}^{[52]}$ ，采用了 $201\times 201$ 的网格，$400\times$

表 2 不同模型误差对比

<table border=1><tr><td></td><td>1a</td><td>2a</td></tr><tr><td>Nusselt 数误差</td><td>0.98%</td><td>0.14%</td></tr><tr><td>Vrms 数误差</td><td>0.50%</td><td>1%</td></tr></table>

表 1 计算中使用的参数

<table border=1><tr><td>Test</td><td>1a</td><td>2a</td></tr><tr><td>重力加速度, $g\left( {\mathrm{\;m}/{\mathrm{s}}^{2}}\right)$</td><td>10</td><td>10</td></tr><tr><td>模型高, $H\left( \mathrm{\;{km}}\right)$</td><td>1000</td><td>1000</td></tr><tr><td>模型长, $L\left( \mathrm{\;{km}}\right)$</td><td>1000</td><td>1000</td></tr><tr><td>上边界的温度, ${T}_{\text{top }}\left( \mathrm{K}\right)$</td><td>273</td><td>273</td></tr><tr><td>下边界的温度, ${T}_{\text{bottom }}\left( \mathrm{K}\right)$</td><td>1273</td><td>1273</td></tr><tr><td>热导率, $k\left( {\mathrm{\;W}/\left( {\mathrm{m}{\mathrm{K}}^{-1}}\right) }\right)$</td><td>5</td><td>5</td></tr><tr><td>热容, ${C}_{p}\left( {\mathrm{\;J}/\mathrm{{kg}}}\right)$</td><td>1250</td><td>1250</td></tr><tr><td>等效密度, ${\rho }_{0}\left( {\mathrm{\;{kg}}/{\mathrm{m}}^{3}}\right)$</td><td>4000</td><td>4000</td></tr><tr><td>热膨胀系数, $\alpha \left( {1/\mathrm{K}}\right)$</td><td>${2.5} \times  {10}^{-5}$</td><td>${2.5} \times  {10}^{-5}$</td></tr><tr><td>等效粘滞系数: ${\eta }_{0}\left( \mathrm{{Pa}}\mathrm{s}\right)$</td><td>${1.0} \times  {10}^{23}$</td><td>${1.0} \times  {10}^{23}$</td></tr><tr><td>$B$</td><td>0</td><td>$\ln \left( {1000}\right)$</td></tr><tr><td>努赛特数, ${Nu} = \frac{H}{{T}_{\text{bottom }}L}\int \limits_{{x = 0}}^{L}\left( \frac{\partial T}{\partial z}\right) \mathrm{d}x$</td><td>4.8844</td><td>10.066</td></tr><tr><td>残余平均速度,</td><td>42.865</td><td>480.43</td></tr><tr><td>${v}_{\text{rms }} = \frac{H{\rho }_{0}{C}_{p}}{k}\sqrt{\frac{1}{HL}\int \limits_{{x = 0}}^{L}\int \limits_{{y = 0}}^{H}\left( {{v}_{x}^{2} + {v}_{y}^{2}}\right) \mathrm{d}x\mathrm{d}y}$</td><td></td><td></td></tr></table>

644

---

<!-- Page 4 -->

中国科学: 地球科学 2013 年 第 43 卷 第 4 期

400 个追踪点(markers).

边界条件：对于速度场所有的边都为自由边界条件；对于温度场左右两个边界是绝热边界条件 $\left(\partial T/\partial x=0\right)$，顶边界温度为 $T_{top}=273\ K$，底边界温度为 $T_{bottom}$。

取 200 km 处为岩石圈的底边界 $^{[5]}$，其绝热温度为 1573 K，之下为软流圈。计算中时间步长为 5000 年每步，共计算了 1 万步，即计算了 5 Ma。我们分别取了初始时刻和最终时刻垂向平均温度和粘滞系数曲线如图 2(a) 和 (b)。另外我们给出了底边界为 1673 K 时初始时刻和最后时刻的温度场彩色图和速度矢量图，如图 3(a) 和 (b)。

从图 2(b) 中可以看到最终时刻温度曲线仍为稳定情况；而图 3(b) 中虽然我们可以看到速度场的扰动，有速度矢量，但是比较文中我们后来计算的速度场值，底边界为 1673 K 时速度值在  $1 \times 10^{-13}$ 的量级，而发生大规模热侵蚀减薄时速度场值在  $1 \times 10^{-9}$ (图 8)，差了 4 个数量级，所以我们认为底边界为 1673 K 时没

<img src="images/bbox_104_293_491_400.jpg" />

<img src="images/bbox_497_293_892_400.jpg" />

<img src="images/bbox_102_406_494_515.jpg" />

<img src="images/bbox_496_406_893_515.jpg" />

图 1 模型 1a 和模型 2a 努赛特(Nusselt)数与  $V_{rms}$ 值与 benchmark 值对比图

<img src="images/bbox_190_551_496_819.jpg" />

温度 (K)

<img src="images/bbox_504_551_806_819.jpg" />

粘滞系数 (Pa s)

图 2 底边界为 1673 K 时的温度(a)和粘滞系数(b)曲线

645

---

<!-- Page 5 -->

乔彦超等：数值模拟华北克拉通岩石圈热对流侵蚀减薄机制

<img src="images/bbox_105_112_893_368.jpg" />

图3 底边界为 $1673\mathrm{K}$ 时初始时刻(a)和最后时刻(b)的温度场彩色图和速度矢量图图中的计算区域为 $700\mathrm{km}\times 700\mathrm{km}$

有发生大规模热侵蚀，以热传导为主。我们把底边界为 $1673\mathrm{K}$，且温度曲线如图2(a)的情况，设为华北克拉通岩石圈减薄前的能稳定存在的初始克拉通情况。

### 2 数值计算的结果

在如图2初始情况基础上我们计算了底边界受到温度扰动影响，温度增高，华北克拉通岩石圈发生热对流侵蚀减薄的情景。为了全面考虑底边界温度变化对岩石圈减薄速率的影响，我们讨论了初始参考等效粘滞系数分别为 $\eta_0 = 1.0\times 10^{22}\mathrm{Pa}$ s和 $\eta_0 = 1.0\times$ $10^{23}\mathrm{Pa}$ s的两种情形，在这两种条件下，我们分别计算了底边界温度为1773,1873,1973和 $2073\mathrm{K}$ 的4种情况。希望得到不同初始参考等效粘滞系数，不同底边界温度对应的岩石圈减薄曲线以及减薄速率，为研究热侵蚀岩石圈减薄提供定量的数据。

当 $\eta_0 = 1.0\times 10^{22}\mathrm{Pa}$ s时，4个不同底边界温度对应的 $Ra_{\mathrm{max}}$ 如表3.

为了展示岩石圈热侵蚀减薄的过程，我们给出了当粘滞系数 $\eta_0 = 1.0\times 10^{22}\mathrm{Pa}$ s时，不同底边界温度不同时刻对应的温度场结果如图4.

表 3 当 $\eta_{0} = 1.0 \times 10^{22}$ Pa s 时不同温度差对应的 $R a_{\max}$ 值

<table border=1><tr><td>温度差$\Delta \mathrm{T}\left( \mathrm{K}\right)$</td><td>1500</td><td>1600</td><td>1700</td><td>1800</td></tr><tr><td>${Ra}_{\max }$</td><td>12863</td><td>13720</td><td>14578</td><td>15435</td></tr></table>

从图4我们可以看出 $\eta_0 = 1.0\times 10^{22}\mathrm{Pa}$ s时不同底边界温度对应的热侵蚀岩石圈减薄的温度场的发展过程。从图中我们可以看到虽然不同底边界温度，但是他们的减薄过程温度场的发展趋势基本一致，都是先由中间开始，向两边，发展成为三个管道。但是从细节上我们可以发现，底边界温度越高 $2.5\mathrm{Ma}$ 后减薄越剧烈，整个系统更不稳定，而且最终时刻稳定的岩石圈厚度明显薄。通过观察和分析加深了我们对这一过程的理解。同时我们通过计算得到的不同底边界温度对应的岩石圈厚度变化曲线如图5。

$\eta_{0} = 1.0\times 10^{22}\mathrm{Pa}$ s时，不同底边界温度对应的岩石圈厚度变化统计结果如表4.关于岩石圈减薄时间，我们是根据计算数据结果中每一个时刻岩石圈的厚度来判断减薄时间，当减薄厚度不再变化时，即确定为减薄的最终时间.

从上表的计算结果我们可以知道：底边界温度为 $1773\mathrm{K}$ 时，从 $200\sim 126.25\mathrm{km}$ 用了 $15\mathrm{Ma}$，减薄速率为 $4.92\times 10^{-3}\mathrm{m / a}$；底边界温度为 $1873\mathrm{K}$ 时，从 $200\sim 118.75\mathrm{km}$ 用了 $15\mathrm{Ma}$，减薄速率为 $5.42\times 10^{-3}\mathrm{m / a}$；底边界温度为 $1973\mathrm{K}$ 时，从 $200\sim 103.75\mathrm{km}$ 用了 $14.95\mathrm{Ma}$，减薄速率为 $6.44\times 10^{-3}\mathrm{m / a}$；底边界温度为 $2073\mathrm{K}$ 时，从 $200\sim 100.00\mathrm{km}$ 用了 $6.87\times 10^{-3}\mathrm{Ma}$，减薄速率为 $6.87\times 10^{-3}\mathrm{m / a}$；可以看到底边界温度越高，

646

---

<!-- Page 6 -->

中国科学: 地球科学 2013 年 第 43 卷 第 4 期

温度等值线图

<img src="images/bbox_134_127_870_425.jpg" />

图4 $\eta_0 = 1.0\times 10^{22}\mathrm{Pa s}$ 时不同底边界温度对应的不同时刻的温度场分布图

图中从上至下每一行分别对应底边界温度为1773, 1873, 1973和 $2073\mathrm{K}$；图中从左至右对应的时间分别为初始时刻2.5, 5, 7.5, 10和15 Ma。图中每条温度等值线相差 $100\mathrm{K}$

<img src="images/bbox_137_491_860_694.jpg" />

图5 $\eta_0 = 1.0\times 10^{22}\mathrm{Pa s}$ 时不同底边界温度对应的岩石圈厚度变化

图中的短线是误差棒(error bar)，每一个误差棒对应一个数据点

表 4 不同底边界温度对应的岩石圈厚度变化结果

<table border=1><tr><td>底边界温度 ${T}_{\max }\left( \mathrm{K}\right)$</td><td>1773</td><td>1873</td><td>1973</td><td>2073</td></tr><tr><td>岩石圈最终厚度(km)</td><td>126.25</td><td>118.75</td><td>103.75</td><td>100.00</td></tr><tr><td>减薄厚度(km)</td><td>73.75</td><td>81.25</td><td>96.25</td><td>100.00</td></tr><tr><td>减薄时间(Ma)</td><td>15</td><td>15</td><td>14.95</td><td>14.55</td></tr><tr><td>减薄速率(m/a)</td><td>${4.92} \times  {10}^{-3}$</td><td>${5.42} \times  {10}^{-3}$</td><td>${6.44} \times  {10}^{-3}$</td><td>${6.87} \times  {10}^{-3}$</td></tr></table>

减薄速率越快；减薄的时间尺度基本都在十几个百万年，这与地球化学推测的结果基本相符 $^{[5,53]}$ 。同时我们需要指出上面两条线按照我们的数据并没有稳定，最后时刻才是最小值。可能由于数据点相对少，所以得到的曲线形态似乎是水平。

647

---

<!-- Page 7 -->

乔彦超等：数值模拟华北克拉通岩石圈热对流侵蚀减薄机制

为了考虑不同初始参考等效粘滞系数对岩石圈减薄速率计算结果的影响，我们同时计算了当 $\eta_0 = 1.0\times 10^{23}\mathrm{Pa}$ s时的情形.这时四个不同底边界温度对应的 $Ra_{\mathrm{max}}$ 如表5.

为了展示岩石圈热侵蚀减薄的过程，我们给出了当 $\eta_0 = 1.0\times 10^{23}\mathrm{Pa}$ s时不同底边界温度对应的不同时刻的温度场结果如图6.

表 5 当 ${\eta }_{0} = {1.0} \times  {10}^{23}\mathrm{\;{Pa}}\mathrm{s}$ 时不同温度差对应的 ${Ra}_{\max }$ 值

<table border=1><tr><td>温度差$\Delta T(K)$</td><td>1500</td><td>1600</td><td>1700</td><td>1800</td></tr><tr><td>$Ra_{\max }$</td><td>1286</td><td>1372</td><td>1457</td><td>1544</td></tr></table>

从图6我们可以看出 $\eta_0 = 1.0\times 10^{23}\mathrm{Pa}$ s时不同底边界温度对应的热侵蚀岩石圈减薄的温度场的发展过程.加深了我们对这一过程的理解.相比于图4的结果，我们可以发现等效粘滞系数较高时系统要更稳定，尤其是基本只发育中间一个管道，岩石圈最终的厚度也要大一些.而我们对图6不同行进行比较可以发现，2.5Ma时也是底边界温度高上地幔对流系统先活化.底边界温度越高最后时刻稳定岩石圈越薄.同时我们根据计算得到的不同底边界温度对应的岩石圈厚度变化曲线如图7.

$\eta_0 = 1.0\times 10^{23}\mathrm{Pa}$ s时，不同底边界温度对应的岩

温度等值线图

<img src="images/bbox_177_333_825_567.jpg" />

图6 $\eta_0 = 1.0\times 10^{23}\mathrm{Pa}$ s时不同底边界温度对应的不同时刻的温度场分布图

图中从上至下每一行分别对应底边界温度为1773, 1873, 1973和 $2073\mathrm{K}$; 图中从左至右对应的时间分别为初始时刻2.5, 5, 7.5, 10和 $12.5\mathrm{Ma}$. 图中每条温度等值线相差 $100\mathrm{K}$

<img src="images/bbox_125_620_873_822.jpg" />

图7 $\eta_0 = 1.0\times 10^{23}\mathrm{Pa}$ s时不同底边界温度对应的岩石圈厚度变化图中的短线是误差棒(error bar)，每一个误差棒对应一个数据点

648

---

<!-- Page 8 -->

中国科学: 地球科学 2013 年 第 43 卷 第 4 期

石圈厚度变化统计结果如表6.

从图5和7中减薄曲线的形态我们可看出，岩石圈减薄的初始阶段减薄的速率较快，到后来变慢，最终平衡达到一个岩石圈未定存在的状态，曲线类似反对数形状。但是图5等效粘滞系数较小时整个曲线斜率一直都较大，而图7等效粘滞系数较大时，初期减薄曲线斜率较大，后期较小，中间有明显的转折状。说明等效粘滞系数较小时系统不稳定性要更高。

从表6的计算结果我们可以知道，等效粘滞系数 $\eta_0 = 1.0\times 10^{23}\mathrm{Pa}$ s时：底边界温度为 $1773\mathrm{K}$ 时，从$200\sim 135\mathrm{km}$ 用了 $15\mathrm{Ma}$，减薄速率为 $4.33\times 10^{-3}\mathrm{m / a}$；底边界温度为 $1873\mathrm{K}$ 时，从 $200\sim 132.5\mathrm{km}$ 用了 $15\mathrm{Ma}$，减薄速率为 $4.5\times 10^{-3}\mathrm{m / a}$；底边界温度为 $1973\mathrm{K}$ 时，从 $200\sim 127.5\mathrm{km}$ 用了 $14.95\mathrm{Ma}$，减薄速率为 $1.93\times$ $10^{-3}\mathrm{m / a}$；底边界温度为 $2073\mathrm{K}$ 时，从 $200\sim 126.25\mathrm{km}$ 用了 $14\times 10^{-3}\mathrm{Ma}$，减薄速率为 $5.27\times 10^{-3}\mathrm{m / a}$；可以看到同等效粘滞系数 $\eta_0 = 1.0\times 10^{22}\mathrm{Pa}$ s时一样，底边界温度越高，减薄速率越快；减薄的时间尺度基本都在十几个百万年。等效粘滞系数 $\eta_0 = 1.0\times 10^{23}\mathrm{Pa}\mathrm{s}$，底边界为 $2073\mathrm{K}$ 时的减薄速率 $5.27\mathrm{mm / a}$，比等效粘滞系数 $\eta_0 = 1.0\times 10^{23}\mathrm{Pa}\mathrm{s}$ 时底边界为 $1773\mathrm{K}$ 时的减薄速率 $4.33\mathrm{mm / a}$ 大 $21.7\%$。等效粘滞系数 $\eta_0 = 1.0\times 10^{22}\mathrm{Pa}\mathrm{s}$，底边界为 $2073\mathrm{K}$ 时的减薄速率 $6.87\mathrm{mm / a}$，比等效粘滞系数 $\eta_0 = 1.0\times 10^{22}\mathrm{Pa}\mathrm{s}$ 时底边界为 $1773\mathrm{K}$ 时的减薄速率 $4.92\mathrm{mm / a}$ 大 $39.6\%$。等效粘滞系数 $\eta_0 = 1.0\times 10^{22}\mathrm{Pa}\mathrm{s}$ 时底边界为 $2073\mathrm{K}$ 时的减薄速率 $6.87\mathrm{mm / a}$，比等效粘滞系数 $\eta_0 = 1.0\times 10^{23}\mathrm{Pa}\mathrm{s}$，底边界为 $2073\mathrm{K}$ 时的减薄速率 $5.27\mathrm{mm / a}$ 大 $30.36\%$。

表 6 不同底边界温度对应的岩石圈厚度变化结果

<table border=1><tr><td>底边界温度 ${T}_{\max }\left( \mathrm{K}\right)$</td><td>1773</td><td>1873</td><td>1973</td><td>2073</td></tr><tr><td>岩石圈最终厚度(km)</td><td>135</td><td>132.5</td><td>127.5</td><td>126.25</td></tr><tr><td>减薄厚度(km)</td><td>65</td><td>67.5</td><td>72.5</td><td>73.75</td></tr><tr><td>减薄时间(Ma)</td><td>15</td><td>15</td><td>14.7</td><td>14</td></tr><tr><td>减薄速率(m/a)</td><td>${4.33} \times  {10}^{-3}$</td><td>${4.5} \times  {10}^{-3}$</td><td>${4.93} \times  {10}^{-3}$</td><td>${5.27} \times  {10}^{-3}$</td></tr></table>

通过这个结果对比我们可以知道，底边界温度和初始参考等效粘滞系数在这个范围内变化，都是影响结果的重要因素。因此我们给出的不同端员的计算能够比较全面的讨论影响结果的因素。

为了更加深刻的了解岩石圈减薄后的状态，我们给出了底边界为 $2073\mathrm{K}$ 时等效粘滞系数分别为$1.0\times 10^{23}$ 和 $1.0\times 10^{22}\mathrm{Pa}\mathrm{s}$ 时最后时刻的温度场彩色图附加速度矢量图，如图8.

图8中蓝色的直线与 $1623\mathrm{K}$ 温度等值线之间的区域为岩石圈发生减薄的区域，所以我们计算给出的岩石圈减薄厚度是平均值，实际情况要复杂的多.图8(a)为等效粘滞系数 $\eta_0 = 1.0\times 10^{23}\mathrm{Pa}\mathrm{s}$ 时最终时刻的结果，图中我们可以看到岩石圈主要在大约中心

<img src="images/bbox_107_553_455_801.jpg" />

<img src="images/bbox_499_553_891_801.jpg" />

图8底边界为 $2073\mathrm{K}$ 时等效粘滞系数分别为 $1.0\times 10^{23}(\mathrm{a})$ 和 $1.0\times 10^{22}\mathrm{Pa}\mathrm{s}(\mathrm{b})$ 时最后时刻的温度场彩色图附加速度矢量图图中三条黑曲线由上至下分别为773,1273和 $1623\mathrm{K}$ 的温度等值线，蓝色的直线为 $200\mathrm{km}$ 的深度，计算区域为 $700\mathrm{km}\times 700\mathrm{km}$

649

---

<!-- Page 9 -->

乔彦超等：数值模拟华北克拉通岩石圈热对流侵蚀减薄机制

两侧的两个区域发生减薄，速度场表现最后时刻比较稳定，软流圈为两个对流环，上部仍有一个小规模对流环。图8(b)为等效粘滞系数 $\eta_{0}=1.0\times10^{22}$ Pa s时最终时刻的结果，图中岩石圈主要有四个区域发生减薄，而且比起来图(a)岩石圈的整体厚度明显更薄。最终时刻的对流情况更为复杂，没有明显的规律。

## 3 讨论和总结

本文的数值实验采用了有限差分和 MIC 的方法，求解了热流耦合方程，来模拟华北克拉通岩石圈减薄的一种可能机制：即由于地球深部运动的某种影响，造成上地幔底部的温度升高，从而造成上地幔对流加剧，对岩石圈底部造成热侵蚀。本文使用了粘滞系数随温度变化的参数，能较真实的反应实际情况。通过本文的计算我们能得到以下结论。

(1) 本文证实了原来稳定存在的克拉通，如底边界为 1673 K 时的初始情形，在底部温度扰动升高后，由于浮力驱动的小尺度地幔对流加剧能够使岩石圈发生大规模减薄。通过不同端员的计算我们知道岩石圈最多从 200 km 减薄到 100 km，至少减薄到 126.25 km，这个计算结果也符合现在层析成像反演的结果 $^{[5,54-56]}$。

(2) 计算过程中我们讨论了初始参考等效粘滞系数分别为  $\eta_0 = 1.0 \times 10^{22}$ Pa s 和  $\eta_0 = 1.0 \times 10^{23}$ Pa s 的两种情形，在这两种条件下，我们分别计算了底边界温度为 1773, 1873, 1973 和 2073 K 的 4 种情况。从表 4, 6 的结果对比我们可以知道，初始参考等效粘滞系数的值是影响减薄速率结果的重要因素。但是我们知道影响粘滞系数的因素有很多，如温度，压力，应变率和水分等 $^{[35]}$，并且现在能给出的经验关系式也都很有争论 $^{[52,57,58]}$。我们数值实验可以考虑极端情况不同的端员的计算结果，结合以后来自实验或者实际更准确数据能够得到更符合实际的结果。

(3) 通过我们计算可以看到岩石圈的减薄速率基本在 mm/a 的量级，减薄的时间尺度基本都在十几个百万年。我们的计算结果可以结合地球化学的证据 $^{[5,53]}$，为细化岩石圈的减薄时间提供依据。

本文是基于 2 维模型的计算，并且没有考虑 440 和 660 km 不连续界面的影响，进一步的工作可以考虑 3 维以及更全面的因素。但是通过本文的数值实验，我们能更直观的了解华北克拉通岩石圈热侵蚀，并且得到简化情形下，不同端员岩石圈减薄的定量数值。为我们研究华北克拉通破坏提供数值证据。

在热侵蚀机制中，上下地幔界面温度的升高是一个关键因素。什么情况下 660 km 深部温度会升高呢？其中一种假设：根据地球物理资料及岩石学的研究工作，路凤香和郑建平 $^{[59]}$以及袁学诚 $^{[60]}$提出了“蘑菇云”模型，认为软流圈热物质上涌深部作用成为地幔演化的主导作用。另外一种可能性为，大规模地幔对流图像发生了变化是造成这种温度变化的可能原因。例如始于三叠纪初华北和华南陆块的碰撞，将大别-苏鲁造山带左行错移了约 350 km，同时苏鲁造山带发生逆时针旋转。在早白垩世，滨太平洋构造活动中，该断裂进一步向北延伸，发生了约 200 km 的左行平移 $^{[61,62]}$。郯庐断裂带两侧岩石圈结构差异提供了华北克拉通活化中存在软流圈地幔物质上升通道的深部探测证据，加之厚的壳-幔过渡带特征，说明郯庐断裂带及其周边克拉通的破坏方式是以热侵蚀为主导的 $^{[63,64]}$。

另外，地幔存在绝热梯度，计算没有考虑可压缩性，绝热压缩(地幔向下运动)的温度升高或膨胀时候(地幔向上运动)的降低。在不可压缩对流中的温度，应该加上绝热梯度才是真实温度。例如绝热梯度(0.3~0.5 K/km) $^{[65]}$，如果取 0.5 K/km，岩石圈底面下温度 1573 K，700 km 处加上绝热梯度矫正后的温度应该增加： $0.5 \times 500 = 250$ K。因此计算用 2073 K，意味着该深度实际温度应该是  $2073 + 250 = 2323$ K。

本文仅讨论了热侵蚀机制的模拟，没有考虑化学侵蚀。没有考虑相变和拆沉的可能机制。拆沉作为一种可能机制，将在其他文章中予以讨论。

## 参考文献

1 Carlson R W, Pearson D G, James D E. Physical, chemical, and chronological characteristics of continental mantle. Rev Geophys, 2005, 43: RG1001, doi: 10.1029/2004RG000156

2 Menzies M A, Fan W, Zhang M. Palaeozoic and Cenozoic lithoprobes and loss of >120 km of Archaean lithosphere, Sino-Korean Craton, China. In: Prichard H M, Alabaster T, Harris N B W, eds. Magmatic Processes and Plate Tectonics. Geol Soc Spec Pub, 1993, 76: 71–81

3 Griffin W L, Zhang A, O'Reilly S Y, et al. Phanerozoic evolution of the lithosphere beneath the Sino-Korean Craton. In: Flower M, Chung

650

---

<!-- Page 10 -->

中国科学：地球科学 2013 年 第 43 卷 第 4 期

S L, Lo C H, eds. Mantle Dynamics and Plate Interactions in East Asia. Am Geophys Union Geodyn Ser, 1998, 27: 107–126

4 Foley S F. Rejuvenation and erosion of the cratonic lithosphere. Nature Geosci, 2008, 1: 503–510

5 吴福元，徐义刚，高山，等．华北岩石圈减薄与克拉通破坏研究的主要学术争论．岩石学报，2008，24：1145-1174

6 郑永飞，吴福元．克拉通岩石圈的生长和再造．科学通报，2009，54：1945-1949

7 Gao S, Rudnick R, Yuan H, et al. Recycling lower continental crust in the North China Craton. Nature, 2004, 432: 892–897

8 Gao S, Rudnick R, Xu W, et al. Recycling deep cratonic lithosphere and generation of intraplate magmatism in the North China Craton. Earth Planet Sci Lett, 2008, 270: 41–53

9 Zheng J, O'Reilly S, Griffin W, et al. Nature and evolution of Cenozoic lithospheric mantle beneath Shandong Peninsula, Sino-Korean Craton, eastern China. Int Geol Rev, 1998, 40: 471–499

10 Zheng J, Griffin W, O'Reilly S, et al. Mechanism and timing of lithospheric modification and replacement beneath the eastern North China Craton: Peridotitic xenoliths from the 100 Ma Fuxin basalts and a regional synthesis. Geochim Cosmochim Acta, 2007, 71: 5203–5225

11 Xu Y G. Thermo-tectonic destruction of the Archaean lithospheric keel beneath the Sino-Korean craton in China: Evidence, timing and mechanism. Phys Chem Earth, 2001, 26: 747–757

12 Xu Y, Huang X, Ma J, et al. Crust-mantle interaction during the tectonic-thermal reactivation of the North China craton: Constraints from SHRIMP zircon U-Pb chronology and geochemistry of Mesozoic plutons from western Shandong. Contrib Mineral Petrol, 2004, 147: 750–767

13 Zhang H. Transformation of lithospheric mantle through peridotite-melt reaction: A case of Sino-Korean craton. Earth Planet Sci Lett, 2005, 237: 768–780

14 Menzies M, Xu Y, Zhang H, et al. Integration of geology, geophysics and geochemistry: A key to understanding the North China Craton. Lithos, 2007, 96: 1–21

15 Schmeling H, Margant G. Mantle flow and evolution of the lithosphere. Phys Earth Planet Int, 1993, 79: 241–267

16 Schmeling H, Margant G. The influence of second-scale convection on the thickness of continental lithosphere and crust. Tectonophysics, 1991, 189: 281–306

17 Richter F H, Person B. On the interaction of two scales of convection in the mantle. J Geophys Res, 1975, 80: 2529–2541

18 Buck W R. When does small-scale convection begin beneath oceanic lithosphere? Nature, 1985, 313: 775–777

19 Buck W R, Parmentier E M. Convection beneath young oceanic lithosphere: Implications for thermal structure and gravity. J Geophys Res, 1986, 91: 1961–1974

20 Davaille A, Jaupart C. Transient high-Rayleigh-number thermal convection with large viscosity variations. J Fluid Mech, 1993, 253: 141–166

21 Davaille A, Jaupart C. Onset of thermal convection in fluids with temperature-dependent viscosity: Application to the oceanic mantle. J Geophys Res, 1994, 99: 19853–19866

22 Yuen D A, Fleitout L. Thinning of the lithosphere by small-scale convective destabilization. Nature, 1985, 313: 125–128

23 Ogawa M, Schubert G, Zebib A. Numerical simulations of three-dimensional thermal convection in a fluid with strongly temperature-dependent viscosity. J Fluid Mech, 1991, 233: 299–328

24 Dumoulin C, Doin M P, Fleitout L. Numerical simulations of the cooling of an oceanic lithosphere above a convective mantle. Phys Earth Planet Int, 2001, 125: 45–64

25 Marquart G. On the geometry of mantle flow beneath drifting lithospheric plates. Geophys J Int, 2001, 144: 356–372

26 Korenaga J, Jordan T H. Physics of multi-scale convection in the Earth's mantle 1. Onset of sublithospheric convection. J Geophys Res, 2003, 108: B7, 2333, doi: 10.1029/2002JB001760

27 Korenaga J, Jordan T H. On ‘steady state’ heat flow and the rheology of the oceanic mantle. Geophys Res Lett, 2002, 29: 2056, doi: 10.1029/2002GL016085

28 Huang J S, Zhong S, van Hunen J. Controls on sublithospheric small-scale convection. J Geophys Res, 2003, 108: 2405, doi: 10.1029/2003JB002456

29 van Hunen J, Huang J S, Zhong S. The effects of shearing on the onset and vigor of small-scale convection in Newtonian rheology. Geophy Res Lett, 2003, 30: 1991

30 Robinson E M, Parsons B, Daly S F. The effects of a shallow viscosity zone on the apparent compensation of mid-plate swell. Earth Planet Sci Lett, 1987, 82: 335–348

31 叶正仁，王建．上地幔变黏度小尺度对流的数值研究．地球物理学报，2003，46：335-339

32 傅容珊，常筱华，黄建华，等．区域重力异常与上地幔小尺度对流模型．地球物理学报，1994，37(增刊)：249-258

651

---

<!-- Page 11 -->

乔彦超等：数值模拟华北克拉通岩石圈热对流侵蚀减薄机制

33 傅容珊，董树谦，黄建华，等．利用地震层析成象数据反演地幔对流模型的研究．地球物理学报，2002，45（增刊）：136-143

34 傅容珊，黄建华，董树谦，等．利用地震层析成象数据计算地幔对流新模型的探讨．地球物理学报，2003，46：772-778

35 Karato S I, Wu P. Rheology of the upper mantle: A synthesis. Science, 1993, 260: 771–778

36 Katzman R, Zhao L, Jordan T H. High-resolution, two-dimensional vertical tomography of the central Pacific mantle using ScS reverberations and frequency-dependent travel times. J Geophys Res, 1998, 103: 17933–17971

37 Chen L, Zha L, Jordan T H. Full three-dimensional seismic structure of the mantle beneath southwestern Pacific Ocean. EOS Trans AGU, Fall Meet Suppl, Abstract S52F-0699, 2001. 82(47)

38 Montagner J P. Upper mantle low anisotropy channels below the Pacific plate. Earth Planet Sci Lett, 2002, 202: 263–274

39 Ritzwoller M H, Shapiro N, Landuyt W. Two-stage cooling of the Pacific lithosphere, EOS Trans AGU. Spring Meet (Suppl), Abstract S41A-02, 2002, 83(19)

40 Christensen U. Convection with pressure-and temperature-dependent non-Newtonian rheology. Geophys J Int, 1984, 77: 343–384

41 Christensen U. Heat transfer by variable viscosity convection and implications for the Earth's thermal evolution. Phys Earth Planet Int, 1984, 35: 264–282

42 Christensen U, Hager H. 3-D convection with variable viscosity. Geophys J Int, 1991, 104: 213–220

43 Tackley P J. Effect of strongly temperature-dependent viscosity on time-dependent 3-dimensional model of mantle convection. J Geophys Res, 1993, 20: 2187–2190

44 Zhong S, Zuber M T. Role of temperature-dependent viscosity and surface plates in spherical shell models of mantle convection. J Geophys Res, 2000, 105, B5: 11063–11082

45 Boussinesq J. Theorie analytique de la chaleur mise en harmonie avec la thermodynamique et avec la théorie mécanique de la lumière. Gauthier-Villars Paris, 1903, 2: 157–176

46 Rayleigh L. On convective currents in a horizontal layer of fluid, when the higher temperature is on the underside. Philos Mag Ser, 1916, 2: 529–546

47 Ranalli, G. Rheology of the Earth. London: Chapman and Hall, 1995. 413

48 Gerya T V, Yuen D A. Characteristics-based marker-in-cell method with conservative finite-differences schemes for modeling geological flows with strongly variable transport properties. Phys Earth Planet Int, 2003, 140: 295–320

49 Gerya T V, Maresch W V, Willner A P, et al. Inherent gravitational instability of thickened continental crust with regionally developed low-timedium-pressure granulite facies metamorphism. Earth Planet Sci Lett, 2001, 190: 221–235

50 Gerya T V, Perchuk L L, Maresch W V, et al. Thermal regime and gravitational instability of multi-layered continental crust: Implications for the buoyant exhumation of high-grade metamorphic rocks. Eur J Miner, 2002, 14: 687–699

51 Blankenbach B, Busse F, Christensen U, et al. A benchmark comparison for mantle convection codes. Geophys J Int, 1989, 98: 23–38

52 McKenzie D, Roberts J M, Weiss N O. Convection in the earth's mantle: Towards a numerical simulation, J Fluid Mech, 1974, 6: 465–538

53 徐义刚，李洪颜，庞崇进，等．论华北克拉通破坏的时限．科学通报，2009，54：1974–1989

54 Fan W M, Menzies M A. Destruction of aged lower lithosphere and accretion of asthenosphere mantle beneath eastern China. Geotecton Metall, 1992, 16: 171–180

55 Chen L, Zheng T Y, Xu W W. A thinned lithospheric image of the Tanlu fault zone, eastern China: Constructed from wave equation based receiver function migration. J Geophys Res, 2006, 111, doi: 10.1029/2005JBoo3974

56 Chen L, Tao W, Zhao L. Distinct lateral variation of lithospheric thickness in the northeastern North China Craton. Earth Planet Sci Lett, 2008, 267: 56–68

57 McKenzie D, Bowin C. The relationship between bathymetry and gravity in the Atlantic Ocean. J Geophys Res, 1976, 81: 1903–1915

58 McKenzie D, Weiss N. Speculations on the thermal and tectonic history of the earth. Geophys J Roy Astron Soc, 1975, 42: 131–174

59 路凤香，郑建平．中国东部显生宙地幔演化的主要样式：“蘑菇云”模型．地学前缘，2000，7：97–108

60 袁学诚. 秦岭岩石圈速度结构与蘑菇云构造模型. 中国科学 D 辑：地球科学, 1996, 26: 209–215

61 朱光，王勇生，牛漫兰．郯庐断裂带的同造山运动．地学前缘. 2004, 11: 169–182

62 李曙光. 大别山超高压变质岩折返机制与华北-华南陆块碰撞过程. 2004, 11: 63–70

63 朱日祥，郑天愉. 华北克拉通破坏机制与古元古代板块构造体系. 科学通报, 2009, 54: 1950–1961

64 刘贻灿，刘理湘，李曙光，等．大别山北淮阳带西段新元古代浅变质花岗岩的发现及其大地构造意义．科学通报，2010，55：2391–2399

65 McKenzie D, Jackson J, Priestley K. Thermal structure of oceanic and continental lithosphere. Earth Planet Sci Lett, 2005, 233: 337–349

652