import AssistantWidget from './components/AssistantWidget'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <p className="text-gray-400 text-sm select-none">Open the assistant →</p>
      <AssistantWidget />
    </div>
  )
}
