import { getChatGPTUser } from './chatgpt-auth';
import Workspace from './workspace';
export const dynamic='force-dynamic';
export default async function Page(){const user=await getChatGPTUser();return <Workspace signedIn={!!user} email={user?.email||''}/>}
