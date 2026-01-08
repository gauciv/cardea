import { Link } from "react-router-dom";
import { useRef, useState, useEffect, useCallback } from "react";
import { Search, Shield, BarChart3, Zap, Bell, Brain, Monitor, Network, Eye, Activity, AlertTriangle, Lock, Menu, X, Twitter, Linkedin, Github } from "lucide-react";
import cardeaLogo from "../assets/Cardea.png";

// Easing function for smooth transition
const easeOutCubic = (t: number): number => {
  return 1 - Math.pow(1 - t, 3);
};

type AnimationPhase = 'hero' | 'transitioning' | 'final';

const LandingPage = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const useCasesRef = useRef<HTMLDivElement>(null);
  const featuresRef = useRef<HTMLDivElement>(null);
  const [currentFeatureIndex, setCurrentFeatureIndex] = useState(0);
  const [activeTab, setActiveTab] = useState(0);
  const [useCasesVisible, setUseCasesVisible] = useState(false);
  const [featuresVisible, setFeaturesVisible] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  // Transition state
  const [phase, setPhase] = useState<AnimationPhase>('hero');
  const [animationProgress, setAnimationProgress] = useState(0);
  const scrollAccumulatorRef = useRef(0);
  const animationRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);
  
  const SCROLL_THRESHOLD = 50;
  const ANIMATION_DURATION = 800;

  // Lock body scroll during hero phase
  useEffect(() => {
    if (phase === 'hero' || phase === 'transitioning') {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'auto';
    }
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [phase]);

  // Animation loop for transition
  const runTransition = useCallback(() => {
    if (startTimeRef.current === null) {
      startTimeRef.current = performance.now();
    }

    const elapsed = performance.now() - startTimeRef.current;
    const rawProgress = Math.min(elapsed / ANIMATION_DURATION, 1);
    const easedProgress = easeOutCubic(rawProgress);
    
    setAnimationProgress(easedProgress);

    if (rawProgress < 1) {
      animationRef.current = requestAnimationFrame(runTransition);
    } else {
      setPhase('final');
      setFeaturesVisible(true);
      startTimeRef.current = null;
    }
  }, []);

  // Scroll handler for hero phase
  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      if (phase === 'final') return;
      
      e.preventDefault();
      
      if (phase === 'hero') {
        scrollAccumulatorRef.current += Math.abs(e.deltaY);
        if (scrollAccumulatorRef.current >= SCROLL_THRESHOLD) {
          setPhase('transitioning');
          scrollAccumulatorRef.current = 0;
          runTransition();
        }
      }
    };

    window.addEventListener('wheel', handleWheel, { passive: false });
    return () => window.removeEventListener('wheel', handleWheel);
  }, [phase, runTransition]);

  // Progress calculations
  const heroOpacity = phase === 'transitioning' ? 1 - animationProgress : (phase === 'hero' ? 1 : 0);
  const heroTranslateY = phase === 'transitioning' ? -animationProgress * 50 : (phase === 'hero' ? 0 : -50);
  const featuresOpacity = phase === 'transitioning' ? animationProgress : (phase === 'final' ? 1 : 0);
  const featuresTranslateY = phase === 'transitioning' ? (1 - animationProgress) * 40 : (phase === 'final' ? 0 : 40);

  // Intersection Observer for scroll-triggered animations
  useEffect(() => {
    let observer: IntersectionObserver | null = null;

    // Small delay to ensure refs are attached after phase change
    const timeoutId = setTimeout(() => {
      observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.target === useCasesRef.current && entry.isIntersecting) {
              setUseCasesVisible(true);
            }
            if (entry.target === featuresRef.current && entry.isIntersecting) {
              setFeaturesVisible(true);
            }
          });
        },
        { threshold: 0.1 }
      );

      if (useCasesRef.current) {
        observer.observe(useCasesRef.current);
      }
      if (featuresRef.current) {
        observer.observe(featuresRef.current);
      }
    }, 100);

    return () => {
      clearTimeout(timeoutId);
      if (observer) {
        observer.disconnect();
      }
    };
  }, [phase]); // Re-run when phase changes so Use Cases ref can be observed

  const useCaseTabs = [
    {
      label: "SECURITY TEAMS",
      headline: "Stop Threats Before They Spread",
      subtitle: "Real-time detection, not post-mortem analysis",
      features: [
        {
          title: "\"See It, Stop It, Done\"",
          description: "AI-powered anomaly detection catches threats in milliseconds. No more sifting through thousands of alerts—Cardea surfaces what matters and takes action automatically."
        },
        {
          title: "Your Playbook, Automated",
          description: "Define response workflows once. Watch Cardea execute them flawlessly every time. Isolate compromised hosts, block malicious IPs, and notify your team—hands-free."
        }
      ],
      visual: {
        type: 'alert',
        data: [
          { severity: 'critical', message: 'Lateral movement detected - Host isolated', time: '2ms response' },
          { severity: 'warning', message: 'Anomalous DNS queries from 10.0.1.45', time: 'Investigating' },
          { severity: 'info', message: 'New device fingerprinted on VLAN 12', time: 'Baselined' },
        ]
      }
    },
    {
      label: "NETWORK ADMINS",
      headline: "Your Network, Fully Visible",
      subtitle: "Every packet, every flow, every device",
      features: [
        {
          title: "Complete Asset Discovery",
          description: "Know every device on your network—managed or not. Cardea continuously maps your infrastructure, tracks changes, and alerts on unauthorized additions."
        },
        {
          title: "Traffic Intelligence",
          description: "Understand your bandwidth. See which applications dominate, spot bottlenecks before users complain, and catch policy violations in real-time."
        }
      ],
      visual: {
        type: 'network',
        data: { devices: 847, activeFlows: '12.4K', bandwidth: '2.4 Gbps', anomalies: 3 }
      }
    },
    {
      label: "SOC ANALYSTS",
      headline: "Investigate in Minutes, Not Hours",
      subtitle: "Context-rich alerts with automated enrichment",
      features: [
        {
          title: "One Dashboard, Full Context",
          description: "Every alert comes with host history, user context, threat intelligence, and recommended actions. Stop pivoting between 12 tools for basic investigations."
        },
        {
          title: "AI-Assisted Hunting",
          description: "Ask questions in plain English. Cardea searches your network data, correlates events, and surfaces patterns that would take hours to find manually."
        }
      ],
      visual: {
        type: 'timeline',
        data: [
          { time: '14:32:01', event: 'Suspicious PowerShell execution', status: 'detected' },
          { time: '14:32:02', event: 'Process tree analyzed', status: 'enriched' },
          { time: '14:32:03', event: 'Matched MITRE ATT&CK: T1059.001', status: 'classified' },
          { time: '14:32:04', event: 'Host quarantined, ticket created', status: 'resolved' },
        ]
      }
    },
    {
      label: "COMPLIANCE",
      headline: "Audit-Ready, Always",
      subtitle: "Continuous compliance monitoring",
      features: [
        {
          title: "Automated Evidence Collection",
          description: "Generate compliance reports on demand. Cardea maintains audit trails, logs access patterns, and documents security controls—no manual data gathering."
        },
        {
          title: "Policy Enforcement",
          description: "Define security policies once, enforce them everywhere. Get instant alerts when systems drift from compliance baselines."
        }
      ],
      visual: {
        type: 'compliance',
        data: { frameworks: ['SOC 2', 'ISO 27001', 'NIST'], score: 94, lastAudit: '2 days ago', findings: 0 }
      }
    }
  ];

  const features = [
    { icon: Search, text: "Detecting network anomalies in real-time..." },
    { icon: Shield, text: "Analyzing threat patterns with AI..." },
    { icon: BarChart3, text: "Visualizing network traffic flows..." },
    { icon: Zap, text: "Correlating security events automatically..." },
    { icon: Bell, text: "Alerting on suspicious behaviors..." },
    { icon: Brain, text: "Learning normal network baselines..." },
  ];

  const technologies = [
    { icon: Monitor, text: "Microsoft Sentinel - Cloud SIEM platform" },
    { icon: Network, text: "KitNET - AI-powered network anomaly detection" },
    { icon: Eye, text: "Zeek - Network security monitoring framework" },
    { icon: Activity, text: "Suricata - High performance IDS/IPS engine" },
  ];

  const navItems = [
    { name: "Home", href: "/" },
    { name: "Features", href: "#features" },
    { name: "Pricing", href: "#pricing" },
  ];

  // Navigation animation state
  const [navVisible, setNavVisible] = useState(false);
  const [navCompact, setNavCompact] = useState(false);

  useEffect(() => {
    // Animate nav in on mount
    const timer = setTimeout(() => setNavVisible(true), 100);
    return () => clearTimeout(timer);
  }, []);

  // Make nav compact after transition
  useEffect(() => {
    setNavCompact(phase === 'final');
  }, [phase]);

  // Feature card rotation
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentFeatureIndex((prev) => (prev + 1) % features.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [features.length]);

  return (
    <div ref={containerRef}>
      {/* Persistent Navigation - Sleek Modern Design */}
      <nav 
        className="fixed top-0 left-0 right-0 z-50 flex justify-center pt-5 px-4 transition-all duration-700"
        style={{
          opacity: navVisible ? 1 : 0,
          transform: navVisible ? 'translateY(0)' : 'translateY(-20px)',
        }}
      >
        <div 
          className="flex items-center px-3 py-2.5 rounded-2xl transition-all duration-500"
          style={{
            background: navCompact 
              ? 'rgba(10, 15, 30, 0.75)' 
              : 'rgba(15, 25, 45, 0.5)',
            backdropFilter: 'blur(20px) saturate(180%)',
            WebkitBackdropFilter: 'blur(20px) saturate(180%)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
            transform: navCompact ? 'scale(0.97)' : 'scale(1)',
          }}
        >
          <div className="flex items-center justify-center px-3 mr-3">
            <img 
              src={cardeaLogo} 
              alt="Cardea" 
              className="h-8 w-auto object-contain transition-all duration-500"
              style={{ 
                filter: navCompact ? 'brightness(1.15) drop-shadow(0 0 8px rgba(74, 158, 218, 0.3))' : 'brightness(1)', 
                userSelect: 'none', 
                pointerEvents: 'none' 
              }}
              draggable={false}
              onContextMenu={(e) => e.preventDefault()}
              onDragStart={(e) => e.preventDefault()}
            />
          </div>
          
          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-0.5">
            {navItems.map((item, index) => (
              <a 
                key={index} 
                href={item.href} 
                onClick={(e) => {
                  if (item.name === 'Features') {
                    e.preventDefault();
                    if (phase === 'hero') {
                      setPhase('transitioning');
                      runTransition();
                    } else if (phase === 'final') {
                      document.getElementById('use-cases')?.scrollIntoView({ behavior: 'smooth' });
                    }
                  } else if (item.name === 'Home') {
                    e.preventDefault();
                    if (phase !== 'hero') {
                      setPhase('hero');
                      setAnimationProgress(0);
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }
                  }
                }}
                className="px-4 py-2 text-sm text-gray-300 hover:text-white transition-all duration-300 rounded-xl hover:bg-white/[0.06] relative group" 
                style={{ 
                  fontFamily: 'Inter, Nunito, sans-serif',
                  fontWeight: 500,
                  letterSpacing: '0.01em',
                  transitionDelay: `${index * 50}ms`,
                }}
              >
                {item.name}
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-0 h-0.5 bg-gradient-to-r from-[#2674b2] to-[#4a9eda] rounded-full transition-all duration-300 group-hover:w-4" />
              </a>
            ))}
            <Link 
              to="/login" 
              className="px-4 py-2 text-sm text-gray-300 hover:text-white transition-all duration-300 rounded-xl hover:bg-white/[0.06] relative group" 
              style={{ fontFamily: 'Inter, Nunito, sans-serif', fontWeight: 500 }}
            >
              Log In
              <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-0 h-0.5 bg-gradient-to-r from-[#2674b2] to-[#4a9eda] rounded-full transition-all duration-300 group-hover:w-4" />
            </Link>
            <Link 
              to="/login" 
              className="ml-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 hover:scale-[1.02] active:scale-[0.98]" 
              style={{ 
                background: 'linear-gradient(135deg, #2674b2 0%, #3d8fd4 100%)',
                color: 'white', 
                fontFamily: 'Inter, Nunito, sans-serif',
                letterSpacing: '0.02em',
                boxShadow: navCompact 
                  ? '0 0 24px rgba(38, 116, 178, 0.5), 0 4px 12px rgba(0, 0, 0, 0.3)' 
                  : '0 4px 16px rgba(38, 116, 178, 0.25), 0 2px 8px rgba(0, 0, 0, 0.2)',
              }}
            >
              Get Started
            </Link>
          </div>
          
          {/* Mobile Hamburger Button */}
          <button
            className="md:hidden p-2 text-gray-300 hover:text-white transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
        
        {/* Mobile Menu Dropdown */}
        {mobileMenuOpen && (
          <div 
            className="md:hidden absolute top-full left-0 right-0 mt-2 mx-4 rounded-2xl overflow-hidden"
            style={{
              background: 'rgba(10, 15, 30, 0.95)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
            }}
          >
            <div className="flex flex-col p-4 space-y-2">
              {navItems.map((item, index) => (
                <a
                  key={index}
                  href={item.href}
                  onClick={(e) => {
                    setMobileMenuOpen(false);
                    e.preventDefault();
                    if (item.name === 'Features') {
                      if (phase === 'hero') {
                        setPhase('transitioning');
                        runTransition();
                      } else if (phase === 'final') {
                        document.getElementById('use-cases')?.scrollIntoView({ behavior: 'smooth' });
                      }
                    } else if (item.name === 'Home') {
                      if (phase !== 'hero') {
                        setPhase('hero');
                        setAnimationProgress(0);
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                      }
                    }
                  }}
                  className="px-4 py-3 text-gray-300 hover:text-white hover:bg-white/10 rounded-xl transition-all"
                  style={{ fontFamily: 'Inter, Nunito, sans-serif', fontWeight: 500 }}
                >
                  {item.name}
                </a>
              ))}
              <Link
                to="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="px-4 py-3 text-gray-300 hover:text-white hover:bg-white/10 rounded-xl transition-all"
                style={{ fontFamily: 'Inter, Nunito, sans-serif', fontWeight: 500 }}
              >
                Log In
              </Link>
              <Link
                to="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="mt-2 px-4 py-3 rounded-xl text-center font-semibold text-white transition-all"
                style={{
                  background: 'linear-gradient(135deg, #2674b2 0%, #3d8fd4 100%)',
                  fontFamily: 'Inter, Nunito, sans-serif',
                }}
              >
                Get Started
              </Link>
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section - Fixed First Page */}
      {phase !== 'final' && (
      <div 
        className="fixed inset-0 flex flex-col"
        style={{
          opacity: heroOpacity,
          transform: `translateY(${heroTranslateY}vh)`,
          transition: phase === 'transitioning' ? 'none' : 'all 0.3s ease-out',
          zIndex: 10,
          background: `linear-gradient(180deg,
            #000000 0%,
            #000000 15%,
            #0a1525 30%,
            #152540 45%,
            #2a4565 55%,
            #4a7090 65%,
            #7aa5c5 75%,
            #a5cce8 85%,
            #d0e8f5 92%,
            #e8f4fc 100%)
          `
        }}
      >
        {/* Animated aurora layer 1 */}
        <div 
          className="absolute hero-aurora-1 pointer-events-none"
          style={{
            width: '200%',
            height: '200%',
            top: '-50%',
            left: '-50%',
            background: `
              radial-gradient(ellipse 40% 35% at 50% 65%,
                rgba(80, 160, 255, 0.15) 0%,
                rgba(50, 130, 220, 0.08) 40%,
                transparent 70%)
            `,
            filter: 'blur(80px)',
          }}
        />

        {/* Animated aurora layer 2 */}
        <div 
          className="absolute hero-aurora-2 pointer-events-none"
          style={{
            width: '200%',
            height: '200%',
            top: '-50%',
            left: '-50%',
            background: `
              radial-gradient(ellipse 35% 30% at 55% 70%,
                rgba(100, 180, 255, 0.12) 0%,
                rgba(60, 140, 230, 0.05) 45%,
                transparent 75%)
            `,
            filter: 'blur(100px)',
          }}
        />

        {/* Side darkening */}
        <div 
          className="absolute inset-0 pointer-events-none"
          style={{
            background: `linear-gradient(90deg,
              rgba(0, 0, 0, 0.25) 0%,
              transparent 25%,
              transparent 75%,
              rgba(0, 0, 0, 0.25) 100%)
            `
          }}
        />

        {/* Top vignette */}
        <div 
          className="absolute inset-0 pointer-events-none"
          style={{
            background: `linear-gradient(180deg,
              rgba(0, 0, 0, 0.4) 0%,
              transparent 25%)
            `
          }}
        />

        {/* Spacer for navigation */}
        <div className="h-24" />

        {/* Hero Content */}
        <div className="flex-1 flex flex-col items-center justify-center px-4 text-center relative z-10" style={{ marginBottom: '120px' }}>
          <h1 
            className="text-4xl md:text-5xl lg:text-6xl text-white mb-6 animate-fade-in leading-tight"
            style={{ 
              fontFamily: 'Geo, sans-serif', 
              fontWeight: 400, 
              animationDelay: '0.4s', 
              letterSpacing: '0.03em',
              textShadow: '0 2px 4px rgba(0, 0, 0, 0.8), 0 0 30px rgba(0, 0, 0, 0.5)',
            }}
          >
            Simplified Security
            <br />
            with <span 
              className="text-white"
              style={{ textShadow: '0 0 20px rgba(74, 158, 218, 0.6), 0 0 40px rgba(74, 158, 218, 0.3)' }}
            >Agentic AI</span>
          </h1>

          <p 
            className="text-gray-400 text-sm md:text-base max-w-lg mb-10 animate-fade-in"
            style={{ fontFamily: 'Nunito, sans-serif', animationDelay: '0.5s' }}
          >
            AI-driven network security that protects, detects, and responds — so you can focus on what matters.
          </p>

          {/* Feature Cards Carousel */}
          <div className="animate-fade-in" style={{ animationDelay: '0.6s' }}>
            <div className="relative h-16 w-[420px] md:w-[480px] mx-auto" style={{ perspective: '1000px' }}>
              {features.map((feature, index) => {
                const isCurrent = index === currentFeatureIndex;
                const isNext = index === (currentFeatureIndex + 1) % features.length;
                const isPrev = index === (currentFeatureIndex - 1 + features.length) % features.length;
                
                let zIndex = 0, translateY = 0, translateZ = 0, opacity = 0, scale = 1;
                if (isCurrent) { zIndex = 30; translateY = 0; translateZ = 0; opacity = 1; scale = 1; }
                else if (isNext) { zIndex = 20; translateY = 8; translateZ = -20; opacity = 0.5; scale = 0.95; }
                else if (isPrev) { zIndex = 10; translateY = -60; translateZ = -40; opacity = 0; scale = 0.9; }
                else { zIndex = 5; translateY = 16; translateZ = -40; opacity = 0.25; scale = 0.9; }
                
                const IconComponent = feature.icon;
                return (
                  <div key={index} className="absolute inset-0 px-6 py-4 rounded-2xl transition-all duration-500 ease-out" style={{
                    background: 'linear-gradient(135deg, rgba(15, 25, 45, 0.95) 0%, rgba(10, 20, 40, 0.98) 100%)',
                    backdropFilter: 'blur(20px)',
                    border: isCurrent ? '1px solid rgba(74, 158, 218, 0.4)' : '1px solid rgba(255, 255, 255, 0.1)',
                    boxShadow: isCurrent 
                      ? '0 0 20px rgba(74, 158, 218, 0.25), 0 8px 32px rgba(0, 0, 0, 0.4)'
                      : '0 8px 32px rgba(0, 0, 0, 0.3)',
                    zIndex, opacity,
                    transform: `translateY(${translateY}px) translateZ(${translateZ}px) scale(${scale})`,
                  }}>
                    <div className="flex items-center gap-4 h-full">
                      <IconComponent className="w-5 h-5 text-[#4a9eda]" />
                      <span className="text-gray-200 text-sm md:text-base" style={{ fontFamily: 'Nunito, sans-serif' }}>
                        {feature.text}
                      </span>
                    </div>
                  </div>
                );  
              })}
            </div>
          </div>
        </div>

        {/* Technologies Carousel */}
        <div 
          className="absolute bottom-24 left-0 right-0 text-center animate-fade-in select-none z-10" 
          style={{ animationDelay: '0.8s', userSelect: 'none' }}
        >
          <div className="relative w-full overflow-hidden py-4">
            <div 
              className="flex gap-16 items-center carousel-track"
              style={{
                animation: 'scroll-left 35s linear infinite',
                width: 'max-content',
              }}
            >
              {[...technologies, ...technologies, ...technologies, ...technologies].map((tech, index) => {
                const IconComponent = tech.icon;
                return (
                  <div 
                    key={index}
                    className="flex items-center gap-3 whitespace-nowrap px-2 select-none"
                    style={{ userSelect: 'none', pointerEvents: 'none' }}
                  >
                    <IconComponent className="w-5 h-5 text-slate-700" />
                    <span 
                      className="text-slate-700 text-sm font-medium tracking-wide select-none" 
                      style={{ fontFamily: 'Nunito, sans-serif', userSelect: 'none' }}
                    >
                      {tech.text.split(' - ')[0]}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Scroll Indicator */}
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10">
          <div className="flex flex-col items-center gap-2 animate-bounce">
            <span 
              className="text-xs text-slate-600 tracking-wider"
              style={{ fontFamily: 'Nunito, sans-serif' }}
            >
              Scroll to explore
            </span>
            <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </div>
      )}

      {/* Features Section - Second Full Page */}
      <div 
        id="features"
        ref={featuresRef}
        className="relative min-h-screen flex items-center"
        style={{
          opacity: featuresOpacity,
          transform: `translateY(${featuresTranslateY}px)`,
          transition: phase === 'transitioning' ? 'none' : 'all 0.3s ease-out',
          background: 'linear-gradient(180deg, #030508 0%, #050810 30%, #0a1220 100%)'
        }}
      >
        {/* Bottom glow */}
        <div className="absolute inset-0 pointer-events-none" style={{
          background: 'linear-gradient(0deg, rgba(38, 116, 178, 0.9) 0%, rgba(38, 116, 178, 0.5) 20%, rgba(38, 116, 178, 0.15) 40%, transparent 60%)',
          maskImage: 'radial-gradient(ellipse 15% 100% at 50% 100%, black 0%, transparent 100%)',
          WebkitMaskImage: 'radial-gradient(ellipse 15% 100% at 50% 100%, black 0%, transparent 100%)',
        }} />
        <div className="absolute inset-0 pointer-events-none" style={{ background: 'radial-gradient(ellipse 50% 60% at 50% 100%, rgba(38, 116, 178, 0.2) 0%, transparent 70%)' }} />
        <div className="absolute inset-0 pointer-events-none" style={{ background: 'radial-gradient(ellipse 30% 20% at 50% 100%, rgba(100, 180, 255, 0.4) 0%, transparent 60%)' }} />

        <div 
          className={`relative z-10 w-full px-8 md:px-16 lg:px-24 transition-all duration-1000 ${featuresVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'}`}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 max-w-7xl mx-auto">
            <div className="flex flex-col justify-center">
              <h2 className="text-3xl md:text-4xl lg:text-5xl text-white mb-6 leading-tight" style={{ fontFamily: 'Geo, sans-serif', fontWeight: 400 }}>
                Intelligent<br />
                <span className="text-gray-400">detection,</span> <span className="text-white">response,</span><br />
                and <span className="text-blue-400">protection.</span><br />
                <span className="text-gray-500">Powered by AI.</span>
              </h2>
              <Link to="/login" className="mt-6 w-fit flex items-center gap-2 px-6 py-3 rounded-full text-sm font-medium border border-gray-600 text-white hover:bg-white/10 transition-all duration-300" style={{ fontFamily: 'Nunito, sans-serif' }}>
                Get Started
                <span className="w-8 h-8 rounded-full bg-[#2674b2] flex items-center justify-center">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </span>
              </Link>
            </div>
            <div className="flex flex-col justify-center">
              <div className="text-xs tracking-widest text-[#4a9eda] mb-4" style={{ fontFamily: 'Nunito, sans-serif' }}>[ CARDEA SECURITY ]</div>
              <p className="text-gray-400 text-base leading-relaxed mb-4" style={{ fontFamily: 'Nunito, sans-serif' }}>
                Cardea leverages agentic AI to transform network security—automatically detecting anomalies with KitNET, monitoring traffic with Zeek, and blocking threats with Suricata.
              </p>
              <p className="text-gray-500 text-sm leading-relaxed" style={{ fontFamily: 'Nunito, sans-serif' }}>
                Integrated with Microsoft Sentinel for enterprise-grade SIEM capabilities, Cardea provides real-time threat intelligence and automated incident response across your entire infrastructure.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Use Cases Section - Third Full Page */}
      {phase === 'final' && (
      <section 
        id="use-cases"
        ref={useCasesRef}
        className="relative"
        style={{
          background: `linear-gradient(180deg,
            #0a1220 0%,
            #0a1525 5%,
            #0f1a30 15%,
            #152540 35%,
            #1a3050 50%,
            #2a4565 70%,
            #3d6080 85%,
            #4a7090 100%
          )`
        }}
      >
        {/* Subtle aurora glow */}
        <div 
          className="absolute top-0 left-0 right-0 h-96 pointer-events-none"
          style={{
            background: 'radial-gradient(ellipse 80% 50% at 50% 0%, rgba(74, 158, 218, 0.1) 0%, transparent 70%)',
          }}
        />
        
        {/* Full page content area */}
        <div className="relative min-h-screen flex flex-col">
          {/* Tab Navigation */}
          <div 
            className={`pt-20 border-b border-gray-700/50 transition-all duration-700 ${useCasesVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}
          >
            <div className="max-w-7xl mx-auto px-8 md:px-16 lg:px-24">
              <div className="flex gap-0 overflow-x-auto">
                {useCaseTabs.map((tab, index) => (
                  <button
                    key={index}
                    onClick={() => setActiveTab(index)}
                    className={`px-6 py-4 text-xs tracking-widest font-medium whitespace-nowrap transition-all duration-300 border-b-2 ${
                      activeTab === index 
                        ? 'text-[#4a9eda] border-[#4a9eda]' 
                        : 'text-gray-500 border-transparent hover:text-gray-300'
                    }`}
                    style={{ fontFamily: 'Nunito, sans-serif' }}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Content Area */}
          <div 
            className={`max-w-7xl mx-auto px-8 md:px-16 lg:px-24 py-16 md:py-24 transition-all duration-1000 delay-200 ${useCasesVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'}`}
          >
            <div 
              key={activeTab}
              className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center min-h-[600px] animate-fade-in-up"
            >
              {/* Left Side - Text Content */}
              <div className="flex flex-col justify-center">
                <h2 
                  className="text-3xl md:text-4xl lg:text-5xl text-white mb-4 leading-tight"
                  style={{ fontFamily: 'Geo, sans-serif', fontWeight: 400 }}
                >
                  {useCaseTabs[activeTab].headline}
                </h2>
                <p className="text-gray-400 text-lg mb-10" style={{ fontFamily: 'Nunito, sans-serif' }}>
                  {useCaseTabs[activeTab].subtitle}
                </p>

                {useCaseTabs[activeTab].features.map((feature, idx) => (
                  <div 
                    key={idx} 
                    className="mb-8 animate-fade-in-up"
                    style={{ animationDelay: `${(idx + 1) * 150}ms` }}
                  >
                    <h3 className="text-white text-lg font-semibold mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>
                      {feature.title}
                    </h3>
                    <p className="text-gray-400 text-sm leading-relaxed" style={{ fontFamily: 'Nunito, sans-serif' }}>
                      {feature.description}
                    </p>
                  </div>
                ))}
              </div>

              {/* Right Side - Visual */}
              <div className="flex items-center justify-center animate-fade-in-up" style={{ animationDelay: '200ms' }}>
                <div 
                  className="w-full max-w-lg rounded-2xl overflow-hidden"
                  style={{
                    background: 'linear-gradient(135deg, rgba(15, 25, 45, 0.9) 0%, rgba(10, 20, 40, 0.95) 100%)',
                    border: '1px solid rgba(74, 158, 218, 0.2)',
                    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(38, 116, 178, 0.1)',
                  }}
                >
                  {/* Visual Header */}
                  <div className="px-6 py-4 border-b border-gray-700/50 flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500/60" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                    <div className="w-3 h-3 rounded-full bg-green-500/60" />
                    <span className="ml-4 text-xs text-gray-500" style={{ fontFamily: 'Nunito, sans-serif' }}>
                      cardea-dashboard
                    </span>
                  </div>

                  {/* Visual Content */}
                  <div className="p-6">
                    {useCaseTabs[activeTab].visual.type === 'alert' && (
                      <div className="space-y-3">
                        {(useCaseTabs[activeTab].visual.data as Array<{severity: string, message: string, time: string}>).map((alert, idx) => (
                          <div 
                            key={idx}
                            className={`p-4 rounded-lg border ${
                              alert.severity === 'critical' 
                                ? 'bg-red-500/10 border-red-500/30' 
                                : alert.severity === 'warning'
                                ? 'bg-yellow-500/10 border-yellow-500/30'
                                : 'bg-blue-500/10 border-blue-500/30'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex items-start gap-3">
                                <AlertTriangle className={`w-4 h-4 mt-0.5 ${
                                  alert.severity === 'critical' ? 'text-red-400' : 
                                  alert.severity === 'warning' ? 'text-yellow-400' : 'text-blue-400'
                                }`} />
                                <span className="text-sm text-gray-200" style={{ fontFamily: 'Nunito, sans-serif' }}>
                                  {alert.message}
                                </span>
                              </div>
                              <span className={`text-xs px-2 py-1 rounded ${
                                alert.severity === 'critical' ? 'bg-red-500/20 text-red-300' :
                                alert.severity === 'warning' ? 'bg-yellow-500/20 text-yellow-300' :
                                'bg-blue-500/20 text-blue-300'
                              }`} style={{ fontFamily: 'Nunito, sans-serif' }}>
                                {alert.time}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {useCaseTabs[activeTab].visual.type === 'network' && (
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          {Object.entries(useCaseTabs[activeTab].visual.data as {devices: number, activeFlows: string, bandwidth: string, anomalies: number}).map(([key, value], idx) => (
                            <div key={idx} className="p-4 rounded-lg bg-[#0a1525] border border-gray-700/50">
                              <div className="text-2xl font-bold text-[#4a9eda]" style={{ fontFamily: 'Nunito, sans-serif' }}>
                                {value}
                              </div>
                              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1" style={{ fontFamily: 'Nunito, sans-serif' }}>
                                {key.replace(/([A-Z])/g, ' $1').trim()}
                              </div>
                            </div>
                          ))}
                        </div>
                        <div className="h-32 rounded-lg bg-[#0a1525] border border-gray-700/50 flex items-center justify-center">
                          <Network className="w-12 h-12 text-[#2674b2]/50" />
                        </div>
                      </div>
                    )}

                    {useCaseTabs[activeTab].visual.type === 'timeline' && (
                      <div className="space-y-0">
                        {(useCaseTabs[activeTab].visual.data as Array<{time: string, event: string, status: string}>).map((item, idx) => (
                          <div key={idx} className="flex items-start gap-4 pb-4 relative">
                            {idx < 3 && (
                              <div className="absolute left-[7px] top-6 w-0.5 h-full bg-gray-700" />
                            )}
                            <div className={`w-4 h-4 rounded-full flex-shrink-0 mt-1 ${
                              item.status === 'resolved' ? 'bg-green-500' :
                              item.status === 'detected' ? 'bg-red-500' :
                              'bg-[#4a9eda]'
                            }`} />
                            <div className="flex-1">
                              <div className="text-xs text-gray-500 mb-1" style={{ fontFamily: 'Nunito, sans-serif' }}>
                                {item.time}
                              </div>
                              <div className="text-sm text-gray-200" style={{ fontFamily: 'Nunito, sans-serif' }}>
                                {item.event}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {useCaseTabs[activeTab].visual.type === 'compliance' && (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between p-4 rounded-lg bg-[#0a1525] border border-gray-700/50">
                          <span className="text-gray-400 text-sm" style={{ fontFamily: 'Nunito, sans-serif' }}>Compliance Score</span>
                          <span className="text-3xl font-bold text-green-400" style={{ fontFamily: 'Nunito, sans-serif' }}>
                            {(useCaseTabs[activeTab].visual.data as {score: number}).score}%
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {(useCaseTabs[activeTab].visual.data as {frameworks: string[]}).frameworks.map((fw, idx) => (
                            <span 
                              key={idx}
                              className="px-3 py-1.5 rounded-full text-xs bg-[#2674b2]/20 text-[#4a9eda] border border-[#2674b2]/30"
                              style={{ fontFamily: 'Nunito, sans-serif' }}
                            >
                              {fw}
                            </span>
                          ))}
                        </div>
                        <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/30">
                          <div className="flex items-center gap-2">
                            <Lock className="w-4 h-4 text-green-400" />
                            <span className="text-sm text-green-300" style={{ fontFamily: 'Nunito, sans-serif' }}>
                              0 open findings • Last audit {(useCaseTabs[activeTab].visual.data as {lastAudit: string}).lastAudit}
                            </span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div 
            className={`border-t border-gray-600/30 py-12 mt-auto transition-all duration-700 delay-500 ${useCasesVisible ? 'opacity-100' : 'opacity-0'}`}
            style={{ background: 'rgba(0, 0, 0, 0.2)' }}
          >
            <div className="max-w-7xl mx-auto px-8 md:px-16 lg:px-24">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
                {/* Brand */}
                <div className="md:col-span-2">
                  <div className="flex items-center gap-3 mb-4">
                    <img src={cardeaLogo} alt="Cardea" className="h-8 w-auto" />
                  </div>
                  <p className="text-gray-400 text-sm max-w-sm" style={{ fontFamily: 'Nunito, sans-serif' }}>
                    AI-powered network security that protects, detects, and responds automatically.
                  </p>
                </div>
                
                {/* Links */}
                <div>
                  <h4 className="text-white font-semibold mb-4" style={{ fontFamily: 'Nunito, sans-serif' }}>Product</h4>
                  <ul className="space-y-2">
                    <li><a href="#features" className="text-gray-400 hover:text-white text-sm transition-colors" style={{ fontFamily: 'Nunito, sans-serif' }}>Features</a></li>
                    <li><a href="#pricing" className="text-gray-400 hover:text-white text-sm transition-colors" style={{ fontFamily: 'Nunito, sans-serif' }}>Pricing</a></li>
                    <li><a href="#use-cases" className="text-gray-400 hover:text-white text-sm transition-colors" style={{ fontFamily: 'Nunito, sans-serif' }}>Use Cases</a></li>
                  </ul>
                </div>
                
                {/* Legal */}
                <div>
                  <h4 className="text-white font-semibold mb-4" style={{ fontFamily: 'Nunito, sans-serif' }}>Legal</h4>
                  <ul className="space-y-2">
                    <li><a href="/privacy" className="text-gray-400 hover:text-white text-sm transition-colors" style={{ fontFamily: 'Nunito, sans-serif' }}>Privacy Policy</a></li>
                    <li><a href="/terms" className="text-gray-400 hover:text-white text-sm transition-colors" style={{ fontFamily: 'Nunito, sans-serif' }}>Terms of Service</a></li>
                    <li><a href="/security" className="text-gray-400 hover:text-white text-sm transition-colors" style={{ fontFamily: 'Nunito, sans-serif' }}>Security</a></li>
                  </ul>
                </div>
              </div>
              
              {/* Bottom bar */}
              <div className="pt-8 border-t border-gray-700/50 flex flex-col md:flex-row items-center justify-between gap-4">
                <p className="text-gray-500 text-sm" style={{ fontFamily: 'Nunito, sans-serif' }}>
                  © 2026 Cardea Security. All rights reserved.
                </p>
                
                {/* Social Icons */}
                <div className="flex items-center gap-4">
                  <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-[#4a9eda] transition-colors">
                    <Twitter className="w-5 h-5" />
                  </a>
                  <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-[#4a9eda] transition-colors">
                    <Linkedin className="w-5 h-5" />
                  </a>
                  <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-[#4a9eda] transition-colors">
                    <Github className="w-5 h-5" />
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      )}
    </div>
  );
};

export default LandingPage;