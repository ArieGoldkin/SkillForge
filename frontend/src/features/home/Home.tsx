export default function Home() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-6">SkillForge</h1>
      <p className="text-muted-foreground mb-8">
        Intelligent Learning Integration Platform - Analyze technical content and generate AI-ready
        implementation guides
      </p>
      <div className="space-y-4">
        <div className="p-6 border rounded-lg">
          <h2 className="text-2xl font-semibold mb-2">Get Started</h2>
          <p className="text-muted-foreground">
            Enter a URL, video link, or repository to begin analysis
          </p>
        </div>
      </div>
    </div>
  )
}
