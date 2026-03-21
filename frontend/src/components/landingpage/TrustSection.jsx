const PILLS = [
  '🧑‍💻 Software Engineering',
  '📊 Data Science',
  '🎨 Design',
  '💼 Product Management',
  '📈 Marketing',
  '🏥 Healthcare',
  '⚖️ Legal',
  '🏗️ Engineering',
]

export default function TrustSection() {
  return (
    <div className="lp-trust">
      <div className="lp-trust-label">Works with any job type or industry</div>
      <div className="lp-trust-pills">
        {PILLS.map((p) => (
          <div key={p} className="lp-trust-pill">{p}</div>
        ))}
      </div>
    </div>
  )
}