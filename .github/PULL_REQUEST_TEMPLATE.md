# Pull Request

## 📝 Description
<!-- Provide a clear description of your changes -->


## 🔗 Related Issues
<!-- Link to related issues using #issue-number -->
Closes #
Related to #

## 🎯 Type of Change
<!-- Check all that apply -->
- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🎨 Style/UI update (formatting, accessibility improvements)
- [ ] ♻️ Code refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] ✅ Test additions or updates
- [ ] 🔧 Configuration change
- [ ] 🔒 Security fix
- [ ] 🌐 Accessibility improvement
- [ ] 🤖 ML model update

## 🧪 Testing
<!-- Describe the tests you ran and how to reproduce them -->

**Test Configuration:**
- Python Version:
- Node Version:
- OS:
- Edge Device: [Raspberry Pi 4/5 / ThinkPad / Local Development / Other]
- Network Environment: [Home Network / Test Network / Production]

**Test Cases:**
- [ ] Edge AI agent correctly identifies anomalies
- [ ] Azure AI Foundry integration works as expected
- [ ] Dashboard displays information correctly
- [ ] Accessibility features work with screen readers (if UI change)
- [ ] IoT device detection works (if device profile change)

**Manual Testing Steps:**
1. 
2. 
3. 

**Test Results:**
```
Paste test output here
```

## 📊 Checklist
<!-- Ensure your PR meets these requirements -->

### Code Quality
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings or errors
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Code has been formatted (Black for Python, Prettier for JS/TS)

### Documentation
- [ ] I have updated the README (if needed)
- [ ] I have updated SECURITY.md (if security-related)
- [ ] I have added/updated code comments
- [ ] I have updated API documentation (if applicable)
- [ ] I have added setup instructions for new dependencies

### Security
- [ ] I have not committed any API keys, credentials, or secrets
- [ ] I have verified that `.env` files are not included (except `.env.example`)
- [ ] My changes do not introduce new security vulnerabilities
- [ ] I have reviewed edge-to-cloud communication security (if applicable)
- [ ] Sensitive log data is properly sanitized before transmission

### Accessibility (for UI changes)
- [ ] Color contrast meets WCAG 2.1 AA standards
- [ ] UI is navigable with keyboard only
- [ ] Screen reader announces content correctly
- [ ] High-readability fonts are used
- [ ] Focus indicators are visible and clear

### Edge Device Testing (if applicable)
- [ ] Tested on Raspberry Pi 4 or equivalent
- [ ] Tested on Raspberry Pi 5 (if available)
- [ ] Memory usage is acceptable (<500MB for edge agent)
- [ ] CPU usage is reasonable (<50% average)
- [ ] Network bandwidth usage is minimal

### Breaking Changes
- [ ] My changes do NOT break existing functionality
- [ ] OR: I have documented all breaking changes below

**Breaking Changes Details (if applicable):**


## 📸 Screenshots (if applicable)
<!-- Add screenshots to help explain your changes, especially for dashboard/UI updates -->

### Before


### After


## 🎯 Performance Impact
<!-- Describe any performance implications -->
- [ ] No significant performance impact
- [ ] Performance improved (specify metric below)
- [ ] Performance decreased (explain and justify below)

**Performance notes:**
- Memory usage:
- CPU usage:
- Network bandwidth:
- Response time:

## 📦 Dependencies
<!-- List any new dependencies or dependency updates -->
- [ ] No new dependencies added
- [ ] Added dependencies:
  - 
- [ ] Updated dependencies:
  - 

**Justification for new dependencies:**


## 🤖 ML Model Changes (if applicable)
- [ ] Not applicable
- [ ] Model accuracy improved (specify metric)
- [ ] Model size changed (specify size)
- [ ] Training data updated

**Model Performance Metrics:**
- Accuracy:
- False Positive Rate:
- False Negative Rate:
- Inference Time:

## 🌐 IoT Device Support (if applicable)
- [ ] Not applicable
- [ ] Added support for new device type: 
- [ ] Updated existing device profile: 

**Device Details:**
- Manufacturer:
- Model:
- Protocol:
- Known vulnerabilities addressed:

## ♿ Accessibility Checklist (for UI changes)
- [ ] Not applicable
- [ ] Tested with screen reader (specify which: NVDA, JAWS, VoiceOver)
- [ ] Tested with high contrast mode
- [ ] Tested with zoom/magnification (200%)
- [ ] Keyboard navigation works correctly
- [ ] Color is not the only means of conveying information
- [ ] Text alternatives provided for non-text content

## 🔄 Cloud Integration (if applicable)
- [ ] Not applicable
- [ ] Azure AI Foundry integration tested
- [ ] API endpoints work correctly
- [ ] Error handling implemented
- [ ] Rate limiting considered

## 📋 Deployment Considerations
<!-- Will this PR require special deployment steps? -->
- [ ] No special deployment steps required
- [ ] Requires environment variable changes (document below)
- [ ] Requires database migration
- [ ] Requires Azure resource updates
- [ ] Requires edge device firmware update

**Deployment Notes:**


## 🧑‍💼 MSP/Customer Impact
<!-- How will this change affect Managed Service Providers or end customers? -->
- [ ] No customer impact
- [ ] Improves security detection
- [ ] Improves dashboard usability
- [ ] Requires customer action (document below)

**Customer Communication Needed:**


## ✅ Final Review
- [ ] I have reviewed the [Contributing Guidelines](CONTRIBUTING.md)
- [ ] I have checked the [Code of Conduct](CODE_OF_CONDUCT.md)
- [ ] I am ready for this PR to be reviewed
- [ ] I will respond to review comments in a timely manner

## 📝 Additional Notes
<!-- Any other information that reviewers should know -->


---

**For Maintainers:**
- [ ] Code review completed
- [ ] Tests passing in CI/CD
- [ ] Documentation is adequate
- [ ] Security review completed (if needed)
- [ ] Accessibility review completed (if UI change)
- [ ] Ready to merge
