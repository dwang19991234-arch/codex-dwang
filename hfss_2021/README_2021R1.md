# HFSS 2021 R1：内置脚本运行方法

这是为 HFSS 2021 R1 编写的原生 AEDT / IronPython 2.7 脚本，不依赖 PyAEDT，也不用 PowerShell、虚拟环境或 pip。

**尚未在 HFSS 2021 R1 实机执行。** 已做 Python 2 语法兼容性、几何数据一致性及原生 API 调用结构检查；这些不代表 AEDT 建模、网格、求解或收敛已经验证。首次运行如报错，请保留 HFSS Message Manager 与脚本日志。

## 第一步：下载和解压

下载 `downloads/HFSS_2021R1.zip` 并解压。建议放在可写的英文路径，例如：

```text
G:\HFSS\HFSS_2021R1\hfss_2021\
    build_2021.py
    solve_export_2021.py
    README_2021R1.md
```

不要直接在 ZIP 内运行，也不要将脚本放在 HFSS 安装目录、Program Files 或只读目录。

## 第二步：只建模

1. 正常打开 **Ansys Electronics Desktop 2021 R1 / HFSS**。
2. 在顶部菜单点击 **Tools → Run Script…**。
3. 在文件选择框中找到 `build_2021.py`，选中后打开。文件类型如有限制，选择 Python 文件或 All Files。
4. 等待建模完成。脚本新建工程，不改你已有的工程，也不会自动开始求解。
5. 查看 Message Manager。成功时显示 `BUILD COMPLETE`，并在脚本旁生成 `run_年月日_时分秒` 文件夹，内含 `Graphene_Fig2d_2021.aedt`。

如果菜单名称与当前界面不同，请提供 HFSS 顶部菜单截图。不要在独立 CPython 3.11 中执行这两个脚本，因为 `ScriptEnv` 和 `oDesktop` 由 AEDT 内置运行环境提供。

## 第三步：检查模型

工程中应有 `Fig2d_approx_2021` 设计，两个独立 PEC 导体、双槽、扼流结构、`Graphene` 集总端口、`OuterRadiation` 外边界与 `Setup220` 求解设置。

空气与硅计算域显示为透明；如仍挡住金属，可在模型树中临时隐藏它们。显示操作不改变求解几何。

脚本完成后确认：

- 中心端口跨越两个 PEC 导体的 6 μm 间隙，端口参考阻抗为 1000 Ω。
- 左侧信号线经扼流段连续，右侧馈线连接地，两端不能短路。
- HFSS 验证没有错误，空气/硅内部交界面不应有辐射边界。

`run_.../build_log.txt` 记录建模阶段，`validation.log` 为 HFSS 模型检查输出。验证通过不是电磁求解通过。

## 第四步：求解和导出

保持刚生成的 `Fig2d_approx_2021` 设计处于活动状态，再点 **Tools → Run Script…**，运行 `solve_export_2021.py`。

**这个脚本会实际启动 HFSS 求解**，包括自适应网格和两个扫频，可能花费较多时间和内存。脚本不强制设置 HPC 核数，使用本机 HFSS 配置与许可证。模型验证失败时会停止。

成功后，工程的 **Results** 下会出现 S11、输入阻抗和复数 S11 报告；工程所在文件夹中生成 `results_...`，包括：

- `S11_Sweep100_220.csv`：100–220 GHz 插值扫描 S11（dB）。
- `Zin_Sweep100_220.csv`：同一扫描的输入阻抗实部和虚部。
- `S11_CheckDiscrete.csv`、`Zin_CheckDiscrete.csv`：100、110…220 GHz 的离散点。
- `ComplexS11.csv`：复数 S11，可独立检查归一化与输入阻抗。
- `solve_export_log.txt`：求解/导出阶段日志。

这些 CSV 是 HFSS 原生报告格式，表头带单位；**不要直接传给旧版 `hfss/plot_results.py`**，旧脚本要求不同格式。可以直接在 HFSS 中看曲线，或用 Excel/Origin 导入 CSV 作图。阻抗图通常以 Ω 为单位，和论文 kΩ 比较时需要除以 1000。

如果求解完成但报告导出失败，先保留 `.aedt` 和结果文件；无需删除工程或盲目重建。可在 HFSS 中手动创建报告：

- Results → Create Modal Solution Data Report → Rectangular Plot。
- Solution 选择 `Setup220 : Sweep100_220`，主扫描选择 Freq。
- S 参数选择 `S(Graphene,Graphene)`，函数选择 dB。
- Z 参数选择 `Z(Graphene,Graphene)`，分别选择 re、im。

## 设置与收敛

原生版与 PyAEDT 版使用同一组估算尺寸和同一几何轮廓。原生版采用 2021 R1 已有的单频自适应设置，**在扫描上限 220 GHz 加密网格**；设置名 `Setup220`，不是旧脚本的 `Setup130`。

- ΔS = 0.02；最多 15 次，至少 3 次、连续 2 次满足收敛。
- 插值扫描输出 241 点：100–220 GHz，间隔 0.5 GHz。
- 离散核查扫描 13 点：100–220 GHz，间隔 10 GHz。
- PEC 面最大网格长度 12 μm，端口 2 μm。

在工程树右键 Setup220，查看 Convergence；达到最大次数不代表已经收敛。还需要对比插值和离散频点、细化网格，并扩大边界检查稳定性。220 GHz 自适应网格也不保证所有低频谐振都充分收敛，窄峰附近需要额外离散求解和检查。

## 模型假设

槽长约 260 μm、两槽中心距约 125 μm 等尺寸来自论文图 1a 的比例尺估计；不是作者版图。所有基本尺寸集中在 `build_2021.py` 顶部的 `PARAMETERS` 字典，生成后也可在 HFSS Local Variables 中查看。

金属为零厚度 PEC；硅 εr=11.7、σ=1 S/m；省略氧化层、hBN、齿形微结构、有限金属损耗和实体硅透镜；硅延伸到开放边界近似半空间。左端 IF 导线开路。1 kΩ 为石墨烯位置的端口参考，不另放并联电阻。没有计算石墨烯光热电响应或吸收率。

正文未给出足够的端口设置，不能保证作者图 2d 的 S11 采用相同的 1000 Ω 归一化。结果可用于近似结构探索，不代表已准确复现论文曲线。

## 报错时给我什么

先运行建模脚本即可。若失败，发 Message Manager 的第一条红色错误，及 `run_.../build_log.txt` 的末尾内容；不要反复点击运行，以免打开大量新工程。此前安装的 Python 3.11 可以保留，但运行原生建模脚本不需要它。

## 2021 R1 已发现的兼容性修正

用户首次运行在创建 Ground 面时提示真空对象必须启用 Solve Inside。已将所有新建真空面（含布尔工具面和端口面）的 SolveInside 设置为 True；最终导体仍通过 Perfect E 边界定义。已检查传给原生 API 的参数，尚待本机重新运行确认。若遇到此错误，请重新下载修正版，关闭本次失败生成的工程，再运行新脚本。

第二次运行发现旧对象名 `Slot-1_upper` / `Slot-1_lower` 含减号，2021 R1 不接受；已改为 `SlotNeg_upper` / `SlotNeg_lower`，并检查所有生成对象名仅含字母、数字和下划线。几何尺寸与坐标不变。
