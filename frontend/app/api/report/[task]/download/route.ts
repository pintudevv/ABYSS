import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ task: string }> }
) {
  const { task } = await params;

  if (!task) {
    return NextResponse.json({ error: 'Task ID required' }, { status: 400 });
  }

  try {
    const response = await fetch(`${BACKEND_URL}/results/${encodeURIComponent(task)}/download`, {
      headers: { Accept: 'text/plain' },
    });

    if (!response.ok) {
      return NextResponse.json({ error: 'Report not found' }, { status: response.status });
    }

    const text = await response.text();
    
    return new NextResponse(text, {
      status: 200,
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Disposition': `attachment; filename="abyss-report-${task}.txt"`,
      },
    });
  } catch (error) {
    console.error('Download proxy error:', error);
    return NextResponse.json({ error: 'Download failed' }, { status: 500 });
  }
}