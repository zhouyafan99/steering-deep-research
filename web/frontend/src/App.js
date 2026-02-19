
import React, { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';

console.log("APP_VERSION", "2026-02-19-WSLOG-1");

const App = () => {
  const [sessionId, setSessionId] = useState('');
  const [query, setQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [thinkingSteps, setThinkingSteps] = useState([]);
  const ws = useRef(null);
  const lastMessageRef = useRef(null);

  const [steerInstruction, setSteerInstruction] = useState('');

  useEffect(() => {
    setSessionId(uuidv4());
  }, []);

  useEffect(() => {
    if (lastMessageRef.current) {
      lastMessageRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [thinkingSteps]);

  useEffect(() => console.log("STEPS", thinkingSteps), [thinkingSteps]);

  const connectWebSocket = () => {
    if (!sessionId) return;
    const wsUrl = `ws://localhost:8000/ws/${sessionId}`;
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => console.log('WebSocket connected');

    ws.current.onclose = () => {
      console.log('WebSocket disconnected');
      if (!thinkingSteps.some(s => s.type === 'error' && s.message?.includes('Connection lost')))
        setThinkingSteps(prev => [...prev, { type: 'error', message: 'Connection lost. Please refresh the page.'}]);
      setIsStreaming(false);
    };
    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (!thinkingSteps.some(s => s.type === 'error' && s.message?.includes('connection')))
        setThinkingSteps(prev => [...prev, { type: 'error', message: 'An error occurred with the connection.'}]);
      setIsStreaming(false);
    };

    ws.current.onmessage = (event) => {
      console.log("WS_IN_RAW", event.data);
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch (e) {
        console.error("WS_IN_PARSE_FAIL", e);
        return;
      }

      const { type, content, message } = msg;

      switch (type) {
        case 'clarify':
          setThinkingSteps(prev => [...prev, { type: 'clarify', content }]);
          setIsStreaming(false);
          break;
        case 'plan':
        case 'plan_updated':
          setThinkingSteps(prev => [...prev, { type: 'plan', content }]);
          break;
        case 'result':
          setThinkingSteps(prev => [...prev, { type: 'report', content }]);
          setIsStreaming(false);
          break;
        case 'error':
          setThinkingSteps(prev => [...prev, { type: 'error', message: message || 'An unknown error occurred.' }]);
          setIsStreaming(false);
          break;
        case 'steer_ack':
          setThinkingSteps(prev => [...prev, { type: 'info', content: content }]);
          break;
        default:
          console.warn("WS_IN_UNKNOWN", msg);
      }
    };
  };

  const handleSendMessage = () => {
    if (query.trim() === '' || !ws.current || ws.current.readyState !== WebSocket.OPEN) return;
    
    const lastStep = thinkingSteps.length > 0 ? thinkingSteps[thinkingSteps.length - 1] : null;
    const isClarificationAnswer = lastStep && lastStep.type === 'clarify';

    const payload = isClarificationAnswer
      ? { type: 'clarify_answer', answer: query }
      : { type: 'start_research', query: query };

    console.log("WS_OUT", payload);
    ws.current.send(JSON.stringify(payload));
    setThinkingSteps(prev => [...prev, { type: 'user', content: query }]);
    setQuery('');
    setIsStreaming(true);
  };

  const handleSteer = () => {
    if (steerInstruction.trim() === '' || !ws.current || ws.current.readyState !== WebSocket.OPEN) return;
    const payload = { type: 'steer', instruction: steerInstruction };
    console.log("WS_OUT", payload);
    ws.current.send(JSON.stringify(payload));
    setThinkingSteps(prev => [...prev, { type: 'user', content: `(Instruction): ${steerInstruction}` }]);
    setSteerInstruction('');
  };

  useEffect(() => {
    if (sessionId) connectWebSocket();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const renderStep = (step, index) => {
    if (step.type === 'user') {
      return <p key={index} className="text-cyan-300 animate-text-focus-in">{`> ${step.content}`}</p>;
    } 
    if (step.type === 'cot') {
        return (
            <div key={index} className="py-4 animate-text-focus-in">
                <h3 className="font-bold text-yellow-400">思索中...</h3>
                <p className="text-gray-400 whitespace-pre-wrap">{step.content}</p>
            </div>
        );
    }
    if (step.type === 'sites') {
        const sites = step.content.split('\n').filter(s => s.startsWith('Query:'));
        return (
            <div key={index} className="py-4 animate-text-focus-in">
                <h3 className="font-bold text-yellow-400">正在研究的网站...</h3>
                <div className="grid grid-cols-2 gap-2 mt-2">
                    {sites.map((site, i) => <p key={i} className="text-sm text-green-500 truncate">{site.replace('Query: ','')}</p>)}
                </div>
            </div>
        );
    }
    if (step.type === 'info') {
        return (
            <div key={index} className="py-2 animate-text-focus-in">
                <p className="text-sm text-gray-500 italic">{`-- ${step.content} --`}</p>
            </div>
        );
    }
    if (step.type === 'report' || step.type === 'clarify' || step.type === 'error') {
         return (
            <div key={index} className="py-4 animate-text-focus-in">
                <h3 className={`font-bold ${step.type === 'error' ? 'text-red-500' : 'text-yellow-400'}`}>
                    {step.type === 'report' ? '最终报告' : step.type === 'clarify' ? '需要澄清' : '发生错误'}
                </h3>
                <div className="text-gray-300 whitespace-pre-wrap">{step.content || step.message}</div>
            </div>
        );
    }
    if (step.type === 'plan') {
        return (
            <div key={index} className="py-4 animate-text-focus-in">
                <h3 className="font-bold text-yellow-400">执行计划</h3>
                <ul className="list-disc list-inside text-gray-400">
                    {step.content.map((item, i) => <li key={i}>{item}</li>)}
                </ul>
            </div>
        );
    }
    if (step.type === 'sources') {
        return (
            <div key={index} className="py-4 animate-text-focus-in">
                <h3 className="font-bold text-yellow-400">参考来源</h3>
                <div className="flex flex-wrap gap-2 mt-2">
                    {step.content.map((source, i) => (
                        <a href={source.url} target="_blank" rel="noopener noreferrer" key={i} className="text-sm bg-gray-700 text-blue-400 px-2 py-1 rounded-full hover:bg-gray-600 truncate">
                            {source.title || source.url}
                        </a>
                    ))}
                </div>
            </div>
        );
    }
    return null;
  }

  return (
    <div className="min-h-screen bg-black text-green-400 font-pixel flex">
      {/* Left Panel */}
      <div className="w-1/3 border-r border-green-900 p-4 flex flex-col">
        <h1 className="text-2xl animate-text-focus-in">SDR</h1>
        <p className="text-xs text-gray-600 animate-text-focus-in">Steering Deep Research</p>
        <div className="flex-grow"></div>
        <div className="flex">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            className="w-full bg-gray-900 border border-green-800 rounded-l-lg p-2 text-green-300 placeholder-green-700 focus:outline-none focus:ring-1 focus:ring-green-500"
            placeholder="Enter topic..."
            disabled={isStreaming}
          />
          <button
            onClick={handleSendMessage}
            className={`px-4 py-2 border-t border-b border-r border-green-700 rounded-r-lg text-green-300 hover:bg-green-800 disabled:opacity-50`}
            disabled={isStreaming}
          >
            Send
          </button>
        </div>

        {/* Steer Control */}
        <div className="flex mt-2">
            <input
                type="text"
                value={steerInstruction}
                onChange={(e) => setSteerInstruction(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSteer()}
                className="w-full bg-gray-800 border border-yellow-800 rounded-l-lg p-2 text-yellow-300 placeholder-yellow-700 focus:outline-none focus:ring-1 focus:ring-yellow-500"
                placeholder="Steer the research..."
                disabled={!isStreaming}
            />
            <button
                onClick={handleSteer}
                className={`px-4 py-2 border-t border-b border-r border-yellow-700 rounded-r-lg text-yellow-300 hover:bg-yellow-800 disabled:opacity-50`}
                disabled={!isStreaming}
            >
                Steer
            </button>
        </div>
      </div>

      {/* Right Panel */}
      <div className="w-2/3 p-6 overflow-y-auto h-screen">
        {thinkingSteps.map((step, index) => (
          <div key={index} ref={index === thinkingSteps.length - 1 ? lastMessageRef : null}>
            {renderStep(step, index)}
          </div>
        ))}
        {isStreaming && <div className="blinking-cursor" />}
      </div>
    </div>
  );
};

export default App;
