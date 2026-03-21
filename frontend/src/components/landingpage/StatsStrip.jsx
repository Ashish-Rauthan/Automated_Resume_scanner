import { useState, useEffect, useRef } from 'react'

const STATS = [
  { value: 20, suffix: '+', label: 'Resumes per session' },
  { value: 30, suffix: 's', label: 'Average screening time' },
  { value: 95, suffix: '%', label: 'Skill detection accuracy' },
  { value: 3,  suffix: 'x', label: 'Faster than manual review' },
]

function Counter({ target, suffix = '' }) {
  const [count, setCount] = useState(0)
  const ref = useRef(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); obs.disconnect() } },
      { threshold: 0.3 }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  useEffect(() => {
    if (!visible) return
    let start = 0
    const step = target / 60
    const timer = setInterval(() => {
      start += step
      if (start >= target) { setCount(target); clearInterval(timer) }
      else setCount(Math.floor(start))
    }, 16)
    return () => clearInterval(timer)
  }, [visible, target])

  return <span ref={ref}>{count}{suffix}</span>
}

export default function StatsStrip() {
  return (
    <div className="lp-stats">
      <div className="lp-stats-inner">
        {STATS.map((s, i) => (
          <div key={i} className="lp-stat-item">
            <div className="lp-stat-val">
              <Counter target={s.value} suffix={s.suffix} />
            </div>
            <div className="lp-stat-label">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}