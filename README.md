# ClassWidgets 集控仓库

本仓库通过 GitHub Pages 向 ClassWidgets 下发课程表和一次性公告。课程表必须放在仓库根目录独立的 **`课程表/`** 文件夹中；不要再创建或使用 `schedules/` 文件夹。

```text
.
├── manifest.json
├── 课程表/
│   ├── class-a.json
│   └── class-b.json
└── .github/
    ├── scripts/
    │   ├── add_schedule_to_manifest.py
    │   ├── publish_announcement.py
    │   ├── publish_power_command.py
    │   └── select_schedule.py
    └── workflows/
        ├── add-schedule-to-manifest.yml
        ├── publish-announcement.yml
        ├── publish-power-command.yml
        └── select-schedule.yml
```

## 添加课程表

将从 ClassWidgets 导出的课程表 JSON 直接放入 `课程表/`。文件名应使用稳定且可读的名称，例如 `class-a.json` 或 `grade1-class3.json`。课程表文件必须是 UTF-8 JSON，并包含有效的 `meta` 对象。

不要手动计算 SHA-256 或手动维护 `manifest.json` 的 `schedules` 数组。运行“选择集控课程表”工作流后，脚本会重新计算所有课程表哈希并更新清单。

## 加入要下发的课程表

把课程表 JSON 放入 `课程表/` 后，在 GitHub 仓库页面打开 **Actions → 加入集控课程表 → Run workflow**。填写该目录顶层的 JSON 文件名，可选填写设置页显示名称。工作流仅将指定文件注册到 `manifest.json` 的 `schedules` 数组，并计算其 SHA-256；不会改动课程表 JSON、不会改动 `yes.id`，也不会移除清单中已有的其他课程表。

工作流拒绝路径、`../`、绝对路径和非 JSON 文件。再次加入同一个文件时会更新该条目的哈希与显示名称，而不会重复添加。

| 课程表状态 | 是否加入 `manifest.json` | CW 是否下载 |
|---|---:|---:|
| 仅保存在仓库备用 | 否 | 否 |
| 需要下发但不自动切换 | 是，`yes.id=0` 或缺失 | 是 |
| 需要下发并自动切换 | 是，且唯一 `yes.id=1` | 是 |

## 选择要自动切换的课程表

在 GitHub 仓库页面打开 **Actions → 选择集控课程表 → Run workflow**。在输入框中填写你要选择的、位于 `课程表/` 顶层的 JSON 文件名，例如：

```text
class-a.json
```

工作流只接受文件名，不接受路径、`../`、绝对路径或非 JSON 文件。它会执行以下确定性操作：

| 操作 | 结果 |
|---|---|
| 所选文件 | 在课程表 JSON 根对象写入 `"yes": {"id": 1}`。 |
| 同一 `课程表/` 文件夹中的其余 JSON | 写入 `"yes": {"id": 0}`。 |
| `manifest.json` | 重建 `schedules` 数组，更新每份文件的 SHA-256、相对地址与策略版本。 |
| Git 提交 | 仅在内容有变化时，以 `github-actions[bot]` 创建一次可审计提交。 |

ClassWidgets 客户端仅当下发的所有课表中**恰好一份** `yes.id` 为 `1` 时才会自动切换到它。全部为 `0` 时只同步保存；若两份及以上为 `1`，客户端会拒绝自动切换。工作流会确保在正常运行后始终只有所选的一份为 `1`。

> 选择由管理员手动完成。工作流不会根据文件名、课程表名称或设备信息猜测要选哪一份。

## 手动清空自动选择

如果需要让所有课表仅下发而不自动切换，可在仓库本地运行：

```bash
python .github/scripts/select_schedule.py --clear-selection
```

该命令会把 `课程表/` 中所有 JSON 的 `yes.id` 设为 `0`，并同步重建 `manifest.json`。之后提交并推送修改即可。

## 公告

“发布集控公告”工作流保持不变。它只更新 `manifest.json` 中的公告命令，不会修改 `课程表/` 内的文件或其 `yes.id` 参数。

## 下发电源命令

在 GitHub 仓库页面打开 **Actions → 下发集控电源命令 → Run workflow**。工作流仅提供四个固定选项：`restart`（重启）、`shutdown`（关机）、`hibernate`（休眠）和 `sleep`（睡眠）；管理员还必须输入“确认”。

工作流会在 `manifest.json` 中写入一条具有唯一 ID、固定动作和 10 分钟有效期的一次性 `power` 命令。它不支持自由文本命令、Shell 命令、程序路径或命令参数。

> 客户端默认拒绝所有远程电源命令。需要在 CW 的“集控 → 远程电源命令”中，手动开启“允许接收远程电源命令”后才会执行；拉取到有效命令后会立即执行。未授权、过期或已经处理过的命令不会执行。
