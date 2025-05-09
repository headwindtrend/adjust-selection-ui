import sublime
import sublime_plugin

class RegionNudgerCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if self.view.settings().get("region_nudger_active"):
            return

        self.view.settings().set("region_nudger_active", True)
        self.phantom_set = sublime.PhantomSet(self.view, "region_nudger_ui")

        self.view.selection_saved = list(self.view.sel())
        self.regions = list(self.view.sel())
        self.view._region_nudger_command = self  # Allow nudge command access
        self.pref_col = self.view.rowcol(self.regions[0].begin())[1]
        self.draw_ui()

        self.view.add_regions("region_nudger", self.regions)

    def draw_ui(self):
        region = self.regions[len(self.regions)-1] if self.regions else sublime.Region(0)
        point = region.begin()

        html = """
            <body>
                <style>
                    .controls {
                        display: flex;
                        gap: 0.5em;
                        justify-content: center;
                        font-size: 1.2em;
                    }
                    a {
                        text-decoration: none;
                        padding: 0.1em 0.5em;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        background-color: #f0f0f0;
                        color: black;
                    }
                </style>
                <div class="controls">
                    <a href="nudge:-1,0">←</a>
                    <a href="nudge:0,-1">↑</a>
                    <a href="nudge:0,1">↓</a>
                    <a href="nudge:1,0">→</a>
                    <a href="done">✓</a>
                    <a href="cancel">✕</a>
                </div>
            </body>
        """

        phantom = sublime.Phantom(
            sublime.Region(point),
            html,
            sublime.LAYOUT_BLOCK,
            on_navigate=self.handle_nav
        )
        self.phantom_set.update([phantom])

    def handle_nav(self, href):
        if href in ("done", "cancel"):
            self.view.run_command("region_nudger_escape", {"ending_as": href})
            return

        # Parse command like "nudge:-1,0"
        if href.startswith("nudge:"):
            delta = href.replace("nudge:", "")
            dx, dy = map(int, delta.split(","))
            self.nudge_regions(dx, dy)

    def nudge_regions(self, dx, dy):
        self.regions = list(self.view.sel())

        n = 2
        while n:
            n -= 1
            new_regions = []
            new_end = prev_end = 0

            for index, region in enumerate(self.regions):
                calc_beg = new_end - prev_end + region.begin(); prev_end = region.end()
                new_begin = calc_beg if index else self.move_point(calc_beg, dx, dy)
                new_end = new_begin - region.begin() + region.end()
                new_regions.append(sublime.Region(new_begin, new_end))

            # Ensure the last point of the selection doesn't go beyond the overall size
            if new_end > self.view.size():
                dx = self.view.size() - prev_end; dy = 0
                if not dx: return
            else: break

        self.regions = new_regions
        self.view.sel().clear()
        self.view.sel().add_all(self.regions)

        self.draw_ui()

        self.view.add_regions("region_nudger", self.regions)

    def move_point(self, pt, dx, dy):
        if abs(dx) > 1:
            self.pref_col = self.view.rowcol(pt + dx)[1]
            return (pt + dx)

        bott_row = self.view.rowcol(sublime.Region(0, self.view.size()).end())[0]

        row, col = self.view.rowcol(pt)
        new_row = min(max(0, row + dy), bott_row)
        new_col = col + dx

        # Handle edge cases for dx
        if dx and new_col < 0:
            if new_row:
                new_row -= 1
                new_col = len(self.view.line(self.view.text_point(new_row, 0)))
            else:
                new_col = 0
        line_len = len(self.view.line(self.view.text_point(new_row, 0)))
        if dx and new_col > line_len:
            if new_row < bott_row:
                new_row += 1
                new_col = 0
            else:
                new_col = line_len
        if dx:
            self.pref_col = new_col

        # Handle edge cases for dy
        if dy and new_col > line_len:
            new_col = line_len
        elif dy and new_col < self.pref_col:
            new_col = min(self.pref_col, line_len)

        return self.view.text_point(new_row, new_col)

class RegionNudgerListener(sublime_plugin.EventListener):
    def on_text_command(self, view, command_name, args):
        if not view.settings().get("region_nudger_active"):
            return None

        if command_name == 'insert' and args.get("characters") == '\n':
            view.run_command("region_nudger_escape", {"ending_as": "done"})
            return ("noop", {})  # Cancel default movement

        # Block all text modification while region_nudger_active
        if command_name in (
            "insert", "paste", "left_delete", "right_delete", "cut",
            "indent", "unindent", "reindent", "transpose", "undo", "redo",
            "redo_or_repeat", "paste_and_indent", "paste_from_history",
            "commit_completion", "replace_completion_with_next_completion",
            "insert_best_completion", "split_selection_into_lines",
            "run_macro_file", "revert_modification", "swap_line_up",
            "swap_line_down", "delete_word", "toggle_comment", "join_lines",
            "duplicate_line", "replace_completion_with_auto_complete",
            "auto_complete", "sort_lines", "insert_snippet", "wrap_block",
            "auto_indent_tag", "wrap_lines", "upper_case", "lower_case",
            "title_case", "delete_to_mark", "swap_with_mark", "yank",
            "replace_all"):  # Just add to this list if you found any missing
            return ("noop", {})

        # Arrow key handling
        if command_name in ("move", "move_to") and args:
            by = args.get("by")
            forward = args.get("forward", True)

            if by == "characters":
                dx = 1 if forward else -1
                view.run_command("region_nudger_nudge", {"dx": dx, "dy": 0})
                return ("noop", {})

            elif by == "lines":
                dy = 1 if forward else -1
                view.run_command("region_nudger_nudge", {"dx": 0, "dy": dy})
                return ("noop", {})

        # Home / End / Page Up / Page Down
        if command_name == "move_to" and args:
            to = args.get("to")
            if to == "bol":
                view.run_command("region_nudger_jump", {"to": "linebeg"})
                return ("noop", {})
            elif to == "eol":
                view.run_command("region_nudger_jump", {"to": "lineend"})
                return ("noop", {})
            elif to == "bof":
                view.run_command("region_nudger_jump", {"to": "top"})
                return ("noop", {})
            elif to == "eof":
                view.run_command("region_nudger_jump", {"to": "bottom"})
                return ("noop", {})

        if command_name == "move" and args:
            by = args.get("by")
            if by == "pages":
                forward = args.get("forward", True)
                view.run_command("region_nudger_jump", {"to": "pagedown" if forward else "pageup"})
                return ("noop", {})

        return None

    # Although indirectly, this is for blocking character typing or paste (which somehow can bypass the above controlling mechanism, that's why.)
    def on_modified(self, view):
        if view.settings().get("region_nudger_active"):
            view.run_command("undo")

class RegionNudgerEscapeCommand(sublime_plugin.TextCommand):
    def run(self, edit, ending_as):
        if ending_as == "cancel":
            self.view.sel().clear()
            self.view.sel().add_all(self.view.selection_saved)
            self.view.settings().set("adj_sel_cancelled", True)  # A signal for the caller to react
        if hasattr(self.view, "selection_saved"):
            delattr(self.view, "selection_saved")
        self.view.erase_phantoms("region_nudger_ui")
        self.view.settings().erase("region_nudger_active")
        self.view.erase_regions("region_nudger")
        if hasattr(self.view, "_region_nudger_command"):
            del self.view._region_nudger_command

class RegionNudgerJumpCommand(sublime_plugin.TextCommand):
    def run(self, edit, to="top"):
        if to == "top":
            anchor = 0
        elif to == "bottom":
            anchor = self.view.size()
        elif to == "linebeg":
            anchor = self.view.text_point(self.view.rowcol(self.view.sel()[0].begin())[0], 0)
        elif to == "lineend":
            anchor = self.view.text_point(self.view.rowcol(self.view.sel()[0].end())[0], len(self.view.line(self.view.sel()[0].end()))) - len(self.view.sel()[0])
        elif to == "pageup":
            visible_region = self.view.visible_region()
            anchor = visible_region.begin() - visible_region.size()
        elif to == "pagedown":
            visible_region = self.view.visible_region()
            anchor = visible_region.begin() + visible_region.size()
        else:
            return

        delta = anchor - self.view.sel()[0].begin()
        self.view.run_command("region_nudger_nudge", {"dx": delta, "dy": 0})
        self.view.show(self.view.sel()[0])

class RegionNudgerNudgeCommand(sublime_plugin.TextCommand):
    def run(self, edit, dx=0, dy=0):
        if not hasattr(self.view, "_region_nudger_command"):
            return

        cmd = self.view._region_nudger_command
        cmd.nudge_regions(dx, dy)

class RegionNudgerClickListener(sublime_plugin.ViewEventListener):
    def on_text_command(self, command_name, args):
        if command_name != "drag_select":
            return

        if not self.view.settings().get("region_nudger_active"):
            return

        sublime.set_timeout_async(self.adjust_selection_after_click, 50)

    def adjust_selection_after_click(self):
        anchor = self.view.sel()[0].begin()
        self.view.sel().clear()
        self.view.sel().add_all(self.view.get_regions("region_nudger"))
        delta = anchor - self.view.sel()[0].begin()
        self.view.run_command("region_nudger_nudge", {"dx": delta, "dy": 0})
