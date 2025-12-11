# Email Rendering & Testing Guide

## Recent Fix: Playoff Matchup Score Display

### The Issue
When playoff brackets were displayed in email format, scores appeared squashed against team names with no clear separation:
```
#1 ILikeTurtles (Steven Segur)TBD
```

### Root Cause
- Original implementation used CSS flexbox (`display: flex`)
- Gmail and many email clients **don't support flexbox**
- CSS gets stripped, causing layout to collapse

### The Solution
Switched to **table-based layout** with inline styles for maximum email client compatibility.

## Technical Implementation

### Before (Flexbox - Broken in Gmail)
```html
<div class="playoff-team" style="display: flex; justify-content: space-between;">
    <span>Team Name</span>
    <strong>156.34</strong>
</div>
```

### After (Table - Works Everywhere)
```html
<table class="playoff-team" cellpadding="10" cellspacing="0" border="0">
    <tr>
        <td style="width: 75%; padding: 10px;">
            #1 Team Name (Owner)
        </td>
        <td style="width: 25%; padding: 10px; text-align: right; 
                   font-size: 16px; font-weight: bold; color: #2c3e50;">
            156.34
        </td>
    </tr>
</table>
```

## Key Changes in `email.py`

### CSS Simplified (Lines 196-203)
- Removed flexbox and related properties
- Kept only email-safe styles
- Winner highlighting still works via `border-left`

### HTML Structure (Lines 510-525)
- Converted div-based layout to table
- Added `cellpadding` and `cellspacing` for consistent rendering
- Inline styles for critical formatting
- 75%/25% column split for proper spacing

## Email Client Compatibility

### ✅ Now Supported
- Gmail (web, iOS, Android)
- Outlook (all versions)
- Apple Mail
- Yahoo Mail
- Mobile email clients
- Webmail interfaces

### 🎨 Visual Features Preserved
- Team name and score separation
- Right-aligned scores
- Winner highlighting (green background)
- Larger font for scores (16px)
- Consistent padding throughout

## Testing the Email Rendering

### Method 1: Browser Emulation (Quick)
1. Open `email-test.html` or `docs/EMAIL_TESTING_TOOLS.html`
2. Use Chrome DevTools (F12)
3. Toggle Device Toolbar (Ctrl+Shift+M)
4. Test different screen sizes

**Browser Testing Tools:**
- `email-test.html` - Live example with playoff brackets
- `docs/EMAIL_TESTING_TOOLS.html` - Bookmarklets for Gmail CSS simulation
- `test-email-rendering.sh` - Helper script with instructions

### Method 2: Send Real Test Email (Best)
```bash
# Generate email HTML
uv run ff-tracker --env --format email > test-email.html

# Copy HTML and send to yourself via Gmail
# Check on both desktop and mobile
```

### Method 3: Use Bookmarklets (Interactive)
1. Open `docs/EMAIL_TESTING_TOOLS.html` in browser
2. Drag bookmarklets to your bookmarks bar
3. Open your email HTML
4. Click bookmarklets to simulate Gmail restrictions:
   - 🚫 Strip Flexbox
   - 📏 Set Email Width (600px)
   - 📱 Mobile View (320px)
   - 🔍 Show Tables (debug layout)

### Method 4: Professional Tools
- **Mailtrap** (Free) - [mailtrap.io](https://mailtrap.io)
- **Litmus** (Paid) - [litmus.com](https://litmus.com)
- **Email on Acid** (Paid) - [emailonacid.com](https://emailonacid.com)

## Gmail CSS Support Reference

| CSS Feature | Gmail | Alternative |
|------------|-------|-------------|
| `display: flex` | ❌ | Use `<table>` |
| `display: grid` | ❌ | Use `<table>` |
| `position: fixed` | ❌ | Use `position: relative` |
| `@media queries` | ⚠️ Limited | Use max-width on tables |
| `<style>` in head | ⚠️ Partial | Use inline styles |
| Inline styles | ✅ | **Best practice!** |
| `<table>` layouts | ✅ | **Use this!** |
| `border-radius` | ⚠️ Inconsistent | Don't rely on it |
| `background-color` | ✅ | Safe to use |
| `padding`/`margin` | ✅ | Safe inline |

## Verification Checklist

Before sending emails, verify:

- [ ] **Score Separation** - Clear space between name and score
- [ ] **Alignment** - Scores right-aligned in their column
- [ ] **Readability** - Easy to distinguish name from score
- [ ] **Winner Highlight** - Green background on winning teams
- [ ] **Mobile View** - Layout works on narrow screens (< 480px)
- [ ] **Long Names** - Team names wrap without breaking layout
- [ ] **Table Structure** - All matchups use table-based layout
- [ ] **Inline Styles** - Critical styles are inline (not external CSS)

## Using Chrome/Brave DevTools for Testing

### Quick Start
1. **Open HTML file** in Brave/Chrome
2. **Press F12** (or Cmd+Option+I on Mac)
3. **Toggle Device Toolbar** - Click phone icon or Ctrl+Shift+M
4. **Select device** - Try "iPhone 12 Pro", "Pixel 5"
5. **Resize viewport** - Drag to test different widths (320px, 480px, 600px)

### Simulate Gmail CSS Stripping
1. Open DevTools (F12)
2. Go to **Elements** tab
3. Find `<style>` section in `<head>`
4. Right-click on a CSS rule → Delete or disable
5. Watch how layout responds

### Network Throttling
1. Open DevTools
2. Go to **Network** tab
3. Select throttling (e.g., "Fast 3G")
4. Reload page to see how it loads on slow connections

## Troubleshooting

### Scores Still Squashed?
- Verify you're using the latest version of `email.py`
- Check that tables are rendering (use "Show Tables" bookmarklet)
- Send real test email (browser may render differently than Gmail)

### Layout Broken on Mobile?
- Check `@media` query for mobile (<480px)
- Verify table width is percentage-based, not fixed pixels
- Test on actual mobile device or Gmail app

### Styles Not Applying?
- Move critical styles to inline (in the HTML tags)
- Avoid external CSS or `<style>` blocks for important styling
- Use old-school HTML attributes (`cellpadding`, `cellspacing`, `border="0"`)

## Resources

- [Can I Email](https://www.caniemail.com/) - CSS support across email clients
- [Campaign Monitor CSS Guide](https://www.campaignmonitor.com/css/)
- [Email Client Market Share](https://www.litmus.com/email-client-market-share/)
- [HTML Email Best Practices](https://www.campaignmonitor.com/dev-resources/guides/coding-html-emails/)

## Testing Files Created

- `email-test.html` - Sample playoff bracket email (all inline styles)
- `docs/EMAIL_TESTING_TOOLS.html` - Browser bookmarklets for Gmail simulation
- `test-email-rendering.sh` - Terminal helper script with instructions
- `playoff-format-demo.html` - Before/after comparison

## Quick Testing Workflow

```bash
# 1. Run the helper script
./test-email-rendering.sh email-test.html

# 2. Or manually open and test
open -a "Brave Browser" email-test.html

# 3. Generate real output from your data
uv run ff-tracker --env --format email > my-test.html
./test-email-rendering.sh my-test.html
```

## Next Steps

1. ✅ **Test in browser** using `EMAIL_TESTING_TOOLS.html` bookmarklets
2. ✅ **Send test email** to yourself
3. ✅ **Verify on mobile** Gmail app
4. ✅ **Deploy with confidence** knowing it works everywhere!
