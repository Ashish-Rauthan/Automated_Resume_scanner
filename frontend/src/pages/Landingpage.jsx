import { useEffect, useState } from 'react'
import '../components/landingpage/landingpage.css'

import NavBar              from '../components/landingpage/NavBar'
import HeroSection         from '../components/landingpage/HeroSection'
import StatsStrip          from '../components/landingpage/StatsStrip'
import FeaturesSection     from '../components/landingpage/FeaturesSection'
import TrustSection        from '../components/landingpage/TrustSection'
import HowItWorksSection   from '../components/landingpage/HowItWorksSection'
import WhatWeProvideSection from '../components/landingpage/WhatWeProvideSection'
import CTASection          from '../components/landingpage/CTASection'
import Footer              from '../components/landingpage/Footer'


export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <>
      <NavBar scrolled={scrolled} />
      <HeroSection />
      <StatsStrip />
      <FeaturesSection />
      <TrustSection />
      <HowItWorksSection />
      <WhatWeProvideSection />
      <CTASection />
      <Footer />
    </>
  )
}