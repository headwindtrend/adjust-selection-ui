import sublime
import sublime_plugin
import time

class AdjustSelectionUiCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.settings().set("adj_sel_ui_active", True)
        self.selection_saved = list(self.view.sel())
        self.regions = list(self.view.sel())
        if not self.regions:
            print("Make a selection first.")
            return

        self.view.sel().clear()

        if len(self.regions) > 1:
            self.phantom_set = sublime.PhantomSet(self.view, "adj_sel_ui")
            self.selected_index = 0
            self.prompt_region_selection()
        else:
            self.view.sel().add(self.regions[0])
            self.view.run_command("region_nudger")
            self.wait_until_nudger_finishes(lambda: self.after_nudger_done())

    def prompt_region_selection(self):
        def draw_ui():
            top_point = self.view.visible_region().begin()
            region = sublime.Region(top_point, top_point)

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
                        <a href="OK">OK</a>
                        <a href="Cancel">Cancel</a>
                    </div>
                </body>
            """

            phantom = sublime.Phantom(region, html, sublime.LAYOUT_BLOCK, on_navigate=handle_nav)
            self.phantom_set.update([phantom])

        def handle_nav(href):
            if href == "Cancel":
                self.view.window().run_command("hide_overlay")
            elif href == "OK":
                self.view.settings().set("adj_sel_cancelled", "to be erased")
                self.view.window().run_command("hide_overlay")

        def on_region_highlighted(index):
            if index:
                regions_index = index - 1
                self.view.add_regions('focusedRegion', [self.regions[regions_index]], "string", "dot")
                self.view.show(self.regions[regions_index])
            else:
                self.view.add_regions('focusedRegion', self.regions, "string", "dot")
                self.view.show(self.regions[0])
            draw_ui()

        def on_region_selected(index):
            if index == -1:
                if self.view.settings().get("adj_sel_cancelled") == "to be erased":
                    self.view.settings().erase("adj_sel_cancelled")
                else:
                    self.view.settings().set("adj_sel_cancelled", True)  # A signal for the caller to react
                    self.regions = self.selection_saved
                self.clean_up_at_exit()
                return

            self.selected_index = index

            self.view.sel().clear()
            if index:
                self.view.sel().add(self.regions[index - 1])
            else:
                self.view.sel().add_all(self.regions)

            self.view.erase_regions('focusedRegion')
            self.phantom_set.update([sublime.Phantom(sublime.Region(0), "", sublime.LAYOUT_BLOCK)])
            self.view.run_command("region_nudger")

            self.wait_until_nudger_finishes(lambda: self.after_nudger_done(True))

        self.view.add_regions('showScope', self.regions, "string", "", sublime.DRAW_NO_FILL)
        items = ["Altogether"] + [
            ("Region " + str(i + 1) + " @ Line " + str(self.view.rowcol(r.begin())[0]+1) + " Pos " + str(self.view.rowcol(r.begin())[1]+1) + " Length " + str(len(r)) + ": " + str(r)) for i, r in enumerate(self.regions)
        ]
        self.view.window().show_quick_panel(items, on_region_selected, 1, self.selected_index, on_region_highlighted)

    def after_nudger_done(self, reload_quick_panel=False):
        if len(self.view.sel()) < len(self.regions):
            if len(self.view.sel()) == 1:
                self.regions[self.selected_index - 1] = list(self.view.sel())[0]
            else:
                sublime.message_dialog("Expecting a single region but multi-region is returned. Operation cancelled.")
        else:
            if len(self.view.sel()) == len(self.regions):
                self.regions = list(self.view.sel())
            else:
                sublime.message_dialog("Total number of regions thereafter is different than what's before. Operation cancelled.")

        if reload_quick_panel:
            self.view.sel().clear()
            self.prompt_region_selection()
        else:
            self.clean_up_at_exit()

        self.view.settings().erase("adj_sel_cancelled")  # Ensure this signal doesn't remain lingering at "done"

    def wait_until_nudger_finishes(self, on_done, timeout_ms=1000):
        def cancel_operation():
            self.regions = self.selection_saved
            self.clean_up_at_exit()
        def check():
            if not self.view.settings().get("region_nudger_active"):
                if self.view.settings().get("adj_sel_cancelled"):
                    cancel_operation()
                else:
                    on_done()
            else:
                if time.time() - starttime < 300:
                    sublime.set_timeout(check, timeout_ms)
                else:
                    sublime.message_dialog('A selection adjustment process stayed active for "too long". Operation cancelled.')
                    self.view.run_command("region_nudger_escape")
                    self.view.settings().set("adj_sel_cancelled", True)  # A signal for the caller to react
                    cancel_operation()
        self.view.settings().erase("adj_sel_cancelled")  # Ensure this signal doesn't remain lingering as region_nudger just started
        starttime = time.time()
        sublime.set_timeout(check, timeout_ms)

    def clean_up_at_exit(self):
        self.view.erase_phantoms("adj_sel_ui")
        self.view.settings().erase("adj_sel_ui_active")
        self.view.erase_regions('focusedRegion')
        self.view.erase_regions('showScope')

        self.view.sel().clear()
        self.view.sel().add_all(self.regions)
