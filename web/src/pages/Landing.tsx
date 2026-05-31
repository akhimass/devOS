import { Link } from "react-router-dom"
import {
  BarChart3,
  Check,
  FileText,
  FlaskConical,
  Globe,
  Phone,
} from "lucide-react"
import "./landing.css"

const FEATURES = [
  {
    icon: Phone,
    title: "After-hours capture",
    body: "Evenings, nights, and weekends — the calls that used to hit voicemail now become signed cases.",
  },
  {
    icon: Check,
    title: "Instant qualification",
    body: "Confirms injury, treatment, fault, and representation, then scores the lead before it reaches your team.",
  },
  {
    icon: Globe,
    title: "Bilingual intake",
    body: "Seamless English and Spanish handling with a warm handoff to your bilingual staff when needed.",
  },
  {
    icon: FlaskConical,
    title: "Statute-of-limitations checks",
    body: "Flags time-barred matters automatically so you stop wasting consults on cases you can't take.",
  },
  {
    icon: BarChart3,
    title: "Quality, measured",
    body: "Every conversation is evaluated and trended — see exactly how your intake improves over time.",
  },
  {
    icon: FileText,
    title: "Drops into your CRM",
    body: "Qualified leads, transcripts, and summaries flow straight to your inbox, Litify, or Clio.",
  },
] as const

const MOCK_ROWS = [
  { caller: "Maria Delgado", type: "Auto accident", disposition: "Qualified", score: "96", ok: true },
  { caller: "James Okafor", type: "Slip & fall", disposition: "Qualified", score: "91", ok: true },
  { caller: "Priya Nair", type: "Auto accident", disposition: "Declined", score: "88", ok: false },
  { caller: "Carlos Mendoza", type: "Auto · ES", disposition: "Qualified", score: "94", ok: true },
] as const

export default function Landing() {
  return (
    <div className="lp">
      <div className="lp-dark">
        <div className="lp-inner">
          <nav className="lp-nav">
            <div className="lp-brand">
              <span className="lp-logo">FC</span> FirstCall
            </div>
            <div className="lp-navlinks">
              <a href="#features">Features</a>
              <a href="#how">How it works</a>
              <a href="#pricing">Pricing</a>
              <Link to="/signin">Sign in</Link>
            </div>
            <div className="lp-navcta">
              <Link className="lp-btn lp-btn-grad" to="/signin">
                Get started
              </Link>
            </div>
          </nav>

          <div className="lp-hero">
            <div className="lp-pill">
              <span className="gd" /> Now answering in English &amp; Spanish · 24/7
            </div>
            <h1>
              Never miss a case.
              <br />
              Your firm&apos;s intake,
              <br />
              <span className="lp-grad">answered by AI.</span>
            </h1>
            <p className="lp-sub">
              FirstCall picks up every call — day, night, and weekend — qualifies the lead,
              checks the statute of limitations, and books the consult. So your firm only talks
              to cases worth taking.
            </p>
            <div className="lp-herocta">
              <Link className="lp-btn lp-btn-light lp-btn-lg" to="/signin">
                Start free trial →
              </Link>
              <a className="lp-btn lp-btn-ghost lp-btn-lg" href="#how">
                See how it works
              </a>
            </div>
            <div className="lp-trust">
              No credit card required · Live in under 10 minutes · Trusted by 200+ PI firms
            </div>
          </div>
        </div>

        <div className="lp-mockwrap">
          <div className="lp-window">
            <div className="lp-bar">
              <span className="d" style={{ background: "#ff5f57" }} />
              <span className="d" style={{ background: "#febc2e" }} />
              <span className="d" style={{ background: "#28c840" }} />
            </div>
            <div className="lp-shot">
              <div className="lp-msb">
                <div className="b">
                  <i /> FirstCall
                </div>
                <div className="it">Home</div>
                <div className="it">Metrics</div>
                <div className="it">Results</div>
                <div className="it on">Calls</div>
                <div className="it">Overview</div>
              </div>
              <div className="lp-msc">
                <div className="lp-mkpis">
                  <div className="lp-mk">
                    <div className="l">Calls today</div>
                    <div className="v">23</div>
                  </div>
                  <div className="lp-mk">
                    <div className="l">Qualified</div>
                    <div className="v a">14</div>
                  </div>
                  <div className="lp-mk">
                    <div className="l">After-hours</div>
                    <div className="v">11</div>
                  </div>
                </div>
                <div className="lp-mtbl">
                  <div className="r h">
                    <span>Caller</span>
                    <span>Case type</span>
                    <span>Disposition</span>
                    <span>Score</span>
                  </div>
                  {MOCK_ROWS.map((row) => (
                    <div className="r" key={row.caller}>
                      <span>{row.caller}</span>
                      <span>{row.type}</span>
                      <span>
                        <span
                          className="lp-mbadge"
                          style={{
                            background: row.ok ? "var(--lp-green-bg)" : "var(--lp-red-bg)",
                            color: row.ok ? "var(--lp-green-tx)" : "var(--lp-red-tx)",
                          }}
                        >
                          {row.disposition}
                        </span>
                      </span>
                      <span>{row.score}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="lp-spacer" />

      <div className="lp-stats">
        <div className="lp-stat">
          <div className="n">24/7</div>
          <div className="l">Always answering, never on hold</div>
        </div>
        <div className="lp-stat">
          <div className="n">3.2×</div>
          <div className="l">More qualified leads captured</div>
        </div>
        <div className="lp-stat">
          <div className="n">&lt;1s</div>
          <div className="l">Average response latency</div>
        </div>
        <div className="lp-stat">
          <div className="n">$4,200</div>
          <div className="l">Saved monthly vs. answering services</div>
        </div>
      </div>

      <div className="lp-section" id="features">
        <div className="lp-eyebrow">Built for plaintiff firms</div>
        <div className="lp-h2">Everything your intake team does — automatically.</div>
        <p className="lp-lead">
          FirstCall isn&apos;t a generic chatbot. It&apos;s trained on personal-injury intake and
          graded on every call.
        </p>
        <div className="lp-feats">
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <div className="lp-feat" key={title}>
              <div className="ic">
                <Icon className="size-5" strokeWidth={2} />
              </div>
              <h3>{title}</h3>
              <p>{body}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="lp-section" id="how" style={{ paddingTop: 0 }}>
        <div className="lp-eyebrow">Live in minutes</div>
        <div className="lp-h2">Three steps to never missing a call.</div>
        <div className="lp-steps">
          <div className="lp-step">
            <div className="num">1</div>
            <h3>Forward your number</h3>
            <p>
              Point your after-hours or overflow line to FirstCall. No new hardware, no IT project.
            </p>
          </div>
          <div className="lp-step">
            <div className="num">2</div>
            <h3>AI answers &amp; qualifies</h3>
            <p>
              FirstCall greets the caller, gathers the facts, screens the matter, and books the
              consult.
            </p>
          </div>
          <div className="lp-step">
            <div className="num">3</div>
            <h3>Qualified leads, delivered</h3>
            <p>
              You wake up to scored, summarized, ready-to-sign cases — and a full audit trail.
            </p>
          </div>
        </div>
      </div>

      <div className="lp-section" style={{ paddingTop: 0 }}>
        <div className="lp-quote">
          <p>
            &ldquo;FirstCall booked four signed cases in its first weekend — calls we would have lost
            to voicemail. It paid for itself before Monday.&rdquo;
          </p>
          <div className="who">
            <b>Dana Morrison</b> · Managing Partner, Morrison &amp; Associates
          </div>
        </div>
      </div>

      <div className="lp-section" id="pricing" style={{ paddingTop: 0 }}>
        <div className="lp-ctaband">
          <h2>Stop losing cases to voicemail.</h2>
          <p>
            Spin up your firm&apos;s AI intake line today. Free for 14 days — live before your next
            missed call.
          </p>
          <Link className="lp-btn lp-btn-light lp-btn-lg" to="/signin">
            Create your workspace →
          </Link>
        </div>
      </div>

      <div className="lp-footer">
        <div className="lp-footin">
          <div className="lp-brand" style={{ color: "var(--lp-ink)" }}>
            <span className="lp-logo">FC</span> FirstCall
          </div>
          <div className="c">© 2026 FirstCall AI · Built on Pipecat &amp; NVIDIA Nemotron</div>
          <div className="lp-footlinks">
            <a href="#features">Features</a>
            <a href="#pricing">Pricing</a>
            <Link to="/signin">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
