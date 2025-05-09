# adjust-selection-ui
## Sublime Text 3 plugin to relocate selections (individual regions or the whole set) without altering region count, width, or content. Provides a UI for precise selection placement.

this is a sublime text 3 plugin for adjusting selection location (particularly useful in multi-region selection.) it doesn't change the total number of regions, nor does the width of each region throughout. and doesn't bring along with the content neither. all it does is to provide a user-interface for adjusting where the selection (as a whole or any region individually) should be landed.

when multi-region selection moving altogether (as a whole) the distances (in terms of how many characters, not rows/columns) between regions will be preserved.

it has visual buttons (as well as a quick panel in case of multi-region selection) for mouse operation. user can mouseclick the landing position directly if that's considered more convenient than clicking arrows buttons. keyboard operation is another way to move the selection. available shortcuts including: arrow-keys, home, end, pageup, pagedown, ctrl+home, ctrl+end, enter, and esc. during the operation, all sorts of editing/modification of the "buffer" content are disabled. keyboard operation for the quick panel is same as the way sublime text 3 is always.

for the esc key to work properly, the following entry must be added to the key-bindings.
```
	{ "keys": ["escape"],
		"command": "region_nudger_escape",
		"args": {"ending_as": "cancel"},
		"context": [
			{ "key": "setting.region_nudger_active", "operator": "equal", "operand": true }
		]
	},
```

JUST IN CASE, for whatever reason why that this plugin is interrupted and that your file/view/buffer remains editing/modification disabled: just open up your console panel ( usually by ctrl+\` ) and enter the expression below. thereafter, the "disable"ment should be no more. to close the console panel, press esc.
- `view.settings().erase("region_nudger_active")`

# If you appreciate my work, i will be very grateful if you can support my work by making small sum donation thru PayPal with `Send payment to` entered as `headwindtrend@gmail.com`. Thank you very much for your support.
