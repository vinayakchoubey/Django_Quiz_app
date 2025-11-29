# 🎨 QuizMaster UI System - Quick Reference Guide

## 🎯 Color Palette

### Primary Colors
```
Primary Blue:      #0ea5e9  (Hover: #38bdf8)
Dark Blue:         #0284c7  (Main brand color)
Darker Blue:       #0369a1  (Deep accent)
```

### Accent Colors
```
Purple:            #8b5cf6  (Secondary brand)
Pink:              #ec4899  (Highlight)
Orange:            #f59e0b  (Warning)
Green:             #10b981  (Success)
Red:               #ef4444  (Danger)
```

### Neutral Colors
```
White:             #ffffff
Light Gray:        #f8fafc  (Light BG)
Medium Gray:       #e2e8f0  (Borders)
Dark Gray:         #475569  (Text muted)
Black:             #0f172a  (Text main)
```

---

## 📏 Spacing System (8px Grid)

```
xs:  4px
sm:  8px   (standard gap)
md:  16px  (standard padding)
lg:  24px  (section padding)
xl:  32px  (hero section)
2xl: 48px  (large section)
3xl: 64px  (page section)
```

---

## 🎬 Typography Scale

```
H1: 2.5rem  (40px)  - Bold, gradient
H2: 2rem    (32px)  - Bold
H3: 1.5rem  (24px)  - Bold
H4: 1.25rem (20px)  - Bold
H5: 1.1rem  (18px)  - Bold
H6: 1rem    (16px)  - Bold
Body: 1rem  (16px)  - Regular
Small: 0.9rem (14px) - Regular
```

---

## 🎨 Shadow System

```
Small:  0 2px 8px rgba(0,0,0,0.08)
Medium: 0 4px 16px rgba(0,0,0,0.12)
Large:  0 8px 32px rgba(0,0,0,0.16)
XL:     0 16px 48px rgba(0,0,0,0.2)
Glow:   0 0 20px rgba(14,165,233,0.3)
```

---

## 🔘 Button Styles

### Primary Button
```css
Background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)
Color: white
Padding: 0.75rem 1.5rem
Border-radius: 12px
Hover: scale 1.05, box-shadow glow
```

### Secondary Button
```css
Background: transparent
Border: 2px solid #0ea5e9
Color: #0ea5e9
Padding: 0.75rem 1.5rem
Hover: background fill, transform lift
```

### Danger Button
```css
Background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%)
Color: white
Padding: 0.75rem 1.5rem
Hover: scale 1.05, shadow enhance
```

---

## 💳 Card Component

```css
Background: rgba(255,255,255,0.7)  /* Glassmorphism */
Border: 1px solid rgba(255,255,255,0.2)
Border-radius: 16px
Padding: 1.5rem
Backdrop-filter: blur(10px)
Box-shadow: 0 4px 16px rgba(0,0,0,0.12)
Hover: translateY(-8px), shadow enhance, border glow
```

---

## 📝 Form Components

### Input Field
```css
Background: rgba(255,255,255,0.6)
Border: 2px solid rgba(255,255,255,0.1)
Border-radius: 10px
Padding: 0.75rem 1rem
Focus: border-color primary, box-shadow glow
```

### Label
```css
Font-weight: 600
Color: var(--text-main)
Margin-bottom: 0.5rem
Font-size: 0.95rem
```

---

## 🎬 Animation Library Quick Reference

### Entrance Animations (0.6s)
```
fadeIn          - Opacity 0→1
fadeInUp        - Opacity 0→1, translateY 20px→0
fadeInDown      - Opacity 0→1, translateY -20px→0
slideInLeft     - Opacity 0→1, translateX -30px→0
slideInRight    - Opacity 0→1, translateX 30px→0
zoomIn          - Opacity 0→1, scale 0.9→1
bounceIn        - Scale 0.3→1.05→1
```

### Hover Animations
```
.hover-scale    - scale 1.05
.hover-lift     - translateY -4px, shadow enhance
.hover-glow     - box-shadow glow
.hover-color    - color transition
.hover-rotate   - rotate 5deg
```

### Continuous Animations
```
bounce          - float up/down 10px
float           - float up/down 20px
scalePulse      - scale 1→1.05→1
glowPulse       - shadow pulse
rotate          - 360deg rotation
```

---

## 📱 Responsive Breakpoints

```
Mobile:         < 480px
Tablet:         480px - 768px
Desktop:        > 768px
Large Desktop:  > 1200px
```

### Layout Changes
```
Mobile:   Single column, full width buttons
Tablet:   2-column grid, stacked on some
Desktop:  3+ column grid, flexible layout
```

---

## 🌓 Dark Theme Variables

```css
--bg-main:           #0f172a
--bg-secondary:      #1e293b
--bg-tertiary:       #334155
--text-main:         #e2e8f0
--text-muted:        #94a3b8
--card-bg:           rgba(30,41,59,0.6)
```

---

## 📊 Component States

### Buttons
```
Normal:    Primary gradient
Hover:     Scale 1.05, shadow enhance
Active:    Ripple effect
Disabled:  opacity 0.5, no transform
```

### Cards
```
Normal:    Shadow md, border subtle
Hover:     translateY -8px, shadow lg, border glow
Active:    border-color primary
```

### Forms
```
Normal:    Border subtle, background light
Focus:     Border primary, shadow glow, background bright
Error:     Border danger, background light red
```

---

## 🎨 Gradient Examples

### Primary Gradient
```css
background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
```

### Secondary Gradient
```css
background: linear-gradient(135deg, #8b5cf6 0%, #0ea5e9 100%);
```

### Warning Gradient
```css
background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
```

### Success Gradient
```css
background: linear-gradient(135deg, #10b981 0%, #059669 100%);
```

### Danger Gradient
```css
background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
```

---

## ⚡ Performance Tips

### Use Hardware Acceleration
```css
transform: translateY(-8px);  ✅ Fast
top: -8px;                    ❌ Slow
```

### Use Transitions Wisely
```css
transition: all 0.3s ease;    ✅ Good
transition: all 0.1s ease;    ✅ Fast feedback
transition: all 1s ease;      ❌ Too slow
```

### CSS Animations vs JavaScript
```css
CSS:        ✅ GPU accelerated, 60 FPS
JavaScript: ❌ CPU intensive, often 30-60 FPS
```

---

## 🎯 Quick Class Usage

### Animations
```html
<div class="animate-fadeInUp">Fade in from bottom</div>
<div class="hover-lift">Lift on hover</div>
<div class="animate-bounce">Bounce continuously</div>
<div class="stagger-item">Staggered entrance</div>
```

### Colors
```html
<span class="text-gradient">Gradient text</span>
<div class="badge badge-primary">Primary badge</div>
<div class="alert alert-success">Success alert</div>
```

### Layout
```html
<div class="container">Max width 1200px</div>
<div class="rounded-xl">Rounded corners</div>
<div class="shadow-lg">Large shadow</div>
```

---

## 📱 Mobile-First Approach

```css
/* Mobile first (default) */
.grid { grid-template-columns: 1fr; }

/* Tablet and up */
@media (min-width: 768px) {
    .grid { grid-template-columns: repeat(2, 1fr); }
}

/* Desktop and up */
@media (min-width: 1024px) {
    .grid { grid-template-columns: repeat(3, 1fr); }
}
```

---

## ♿ Accessibility Checklist

- ✅ Color contrast ratio ≥ 4.5:1 for text
- ✅ Keyboard navigation support
- ✅ Semantic HTML structure
- ✅ ARIA labels for buttons
- ✅ Focus states visible
- ✅ Reduced motion support
- ✅ Form error messages
- ✅ Icon + text combinations

---

## 🔧 Common Customizations

### Change Brand Color
```css
/* In premium.css */
--primary: #YOUR_COLOR;
--primary-dark: #DARKER_SHADE;
--primary-light: #LIGHTER_SHADE;
```

### Adjust Border Radius
```css
border-radius: 16px;  /* Current */
border-radius: 12px;  /* Less round */
border-radius: 20px;  /* More round */
```

### Modify Shadow Intensity
```css
box-shadow: 0 4px 16px rgba(0,0,0,0.12);  /* Current */
box-shadow: 0 2px 8px rgba(0,0,0,0.08);   /* Subtle */
box-shadow: 0 8px 32px rgba(0,0,0,0.2);   /* Strong */
```

---

## 📚 File Organization

```
static/
├── css/
│   ├── premium.css          (880 lines - Main design system)
│   ├── animations.css       (500+ lines - Animation library)
│   └── style.css            (Legacy - can be deprecated)

templates/
├── base.html                (Updated - theme toggle, navbar)
├── users/
│   ├── login.html           (Redesigned)
│   └── register.html        (Redesigned)
└── quizzes/
    └── quizzes/
        ├── home.html        (Enhanced)
        ├── quiz_detail.html (Enhanced)
        └── question.html    (Minor updates)
```

---

## 🚀 Deployment Checklist

- ✅ CSS files minified
- ✅ Images optimized
- ✅ No console errors
- ✅ Responsive tested (480px, 768px, 1200px)
- ✅ Dark/Light theme works
- ✅ All buttons functional
- ✅ Forms submit correctly
- ✅ Animations smooth (60 FPS)
- ✅ Accessibility tested
- ✅ Performance optimized

---

**Created**: November 28, 2025
**Status**: ✅ Ready to Use
**Version**: 1.0
